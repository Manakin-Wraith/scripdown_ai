# Database Schema Documentation

## Overview
ScripDown AI uses **Supabase (PostgreSQL)** for production. This document details the current schema with focus on breakdown fields for PDF export enhancement.

---

## Core Tables

### `scripts`
Main script metadata table.

**Current Breakdown-Related Fields:**
- `title` (TEXT) - Script title
- `writer_name` (TEXT) - Writer name
- `draft_version` (TEXT) - Draft version (e.g., "First Draft", "Shooting Draft")
- `production_company` (TEXT) - Production company name
- `contact_email` (TEXT) - Writer/production contact email
- `contact_phone` (TEXT) - Writer/production contact phone
- `total_pages` (INT) - Total page count
- `copyright_info` (TEXT) - Copyright/WGA registration info
- `additional_credits` (TEXT) - Additional credits (e.g., "Based on...")

**Script Management Fields:**
- `is_locked` (BOOLEAN) - Script locked for production
- `locked_at` (TIMESTAMPTZ) - When script was locked
- `locked_by` (UUID) - User who locked script
- `current_revision_color` (VARCHAR) - Current revision color
- `current_version_id` (UUID) - Current version reference

---

### `scenes`
Scene-level data with breakdown information.

**Current Breakdown Fields:**

#### Basic Scene Info
- `scene_number` (VARCHAR) - Scene number (e.g., "1", "15A")
- `scene_order` (INT) - Order in script
- `int_ext` (VARCHAR) - INT/EXT designation
- `setting` (VARCHAR) - Location/setting name
- `time_of_day` (VARCHAR) - DAY/NIGHT/DAWN/DUSK
- `page_start` (INT) - Starting page number
- `page_end` (INT) - Ending page number

#### Breakdown Categories (JSONB Arrays)
- `characters` (JSONB) - Array of character names/objects
- `props` (JSONB) - Array of prop names/objects
- `wardrobe` (JSONB) - **EXISTS** - Array of wardrobe items
- `makeup` (JSONB) - **MISSING** - Makeup requirements
- `special_effects` (JSONB) - **MISSING** - SFX/VFX requirements
- `vehicles` (JSONB) - **MISSING** - Vehicles in scene
- `animals` (JSONB) - **MISSING** - Animals in scene
- `extras` (JSONB) - **MISSING** - Background actors/extras
- `stunts` (JSONB) - **MISSING** - Stunt requirements

#### Scene Content & Analysis
- `scene_text` (TEXT) - Full scene text
- `text_start` (INT) - Character position in full script
- `text_end` (INT) - End character position
- `description` (TEXT) - **EXISTS** - Scene summary/description
- `dialogue` (JSONB) - **EXISTS** - Dialogue excerpts
- `action_description` (TEXT) - **MISSING** - Action line summary
- `emotional_tone` (TEXT) - **MISSING** - Emotional tone/mood
- `technical_notes` (TEXT) - **MISSING** - Technical requirements

#### Analysis Status
- `analysis_status` (VARCHAR) - pending/analyzing/complete/failed
- `is_manual` (BOOLEAN) - Manually created scene

#### Scene Management
- `is_omitted` (BOOLEAN) - Scene marked as omitted
- `omitted_at` (TIMESTAMPTZ) - When omitted
- `original_scene_number` (VARCHAR) - Original number before changes
- `locked_scene_number` (VARCHAR) - Number when locked
- `revision_number` (INT) - Revision number
- `parent_scene_id` (UUID) - Parent if split from another scene
- `merged_into_scene_id` (UUID) - Scene this was merged into

---

## Supporting Tables

### `script_pages`
Stores page-by-page text content.
- `script_id` (UUID)
- `page_number` (INT)
- `page_text` (TEXT)
- `content_hash` (TEXT)

### `script_versions`
Tracks script revisions.
- `version_number` (INT)
- `revision_color` (VARCHAR) - white, blue, pink, yellow, green, goldenrod, buff, salmon, cherry
- `pdf_path` (TEXT)
- `is_locked` (BOOLEAN)

### `scene_history`
Audit trail for scene changes.
- `scene_id` (UUID)
- `change_type` (VARCHAR) - created, modified, omitted, split, merged, reordered
- `previous_data` (JSONB)
- `changed_by` (UUID)

### `reports`
Generated report storage.
- `script_id` (UUID)
- `report_type` (VARCHAR) - scene_breakdown, day_out_of_days, location, props, wardrobe, one_liner, full_breakdown
- `title` (TEXT)
- `config` (JSONB) - Report configuration
- `data_snapshot` (JSONB) - Frozen data at generation time
- `share_token` (TEXT)
- `is_public` (BOOLEAN)
- `expires_at` (TIMESTAMPTZ)

---

## Missing Fields Analysis

### High Priority (Phase 1)
These fields are **missing** from the `scenes` table and needed for comprehensive breakdown reports:

1. **`makeup` (JSONB)** - Makeup & hair requirements
   - Example: `["Blood makeup", "Period hairstyle", "Aging makeup"]`

2. **`special_effects` (JSONB)** - SFX/VFX requirements
   - Example: `["Gunshot squib", "Rain effect", "CGI creature"]`

3. **`vehicles` (JSONB)** - Vehicles in scene
   - Example: `["Police car", "Motorcycle", "Helicopter"]`

4. **`animals` (JSONB)** - Animals in scene
   - Example: `["German Shepherd", "Horses (3)"]`

5. **`extras` (JSONB)** - Background actors/extras
   - Example: `["Crowd (20-30)", "Restaurant patrons (8)"]`

6. **`stunts` (JSONB)** - Stunt requirements
   - Example: `["Car crash", "Fight choreography", "Fall from height"]`

### Medium Priority (Phase 2)
Additional fields for enhanced reporting:

7. **`action_description` (TEXT)** - Summary of action lines
   - Extracted from scene text, describes physical action

8. **`emotional_tone` (TEXT)** - Emotional mood/tone
   - Example: "Tense", "Romantic", "Comedic"

9. **`technical_notes` (TEXT)** - Technical requirements
   - Example: "Requires crane shot", "Low-light conditions"

10. **`sound_notes` (TEXT)** - Sound/music requirements
    - Example: "Diegetic music - jazz club", "Thunder SFX"

---

## Migration Plan

### Option A: Add Missing Columns (Recommended)
Add JSONB columns to `scenes` table for missing breakdown categories.

```sql
-- Migration: 022_enhanced_breakdown_fields.sql

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS makeup JSONB DEFAULT '[]'::jsonb;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS special_effects JSONB DEFAULT '[]'::jsonb;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS vehicles JSONB DEFAULT '[]'::jsonb;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS animals JSONB DEFAULT '[]'::jsonb;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS extras JSONB DEFAULT '[]'::jsonb;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS stunts JSONB DEFAULT '[]'::jsonb;

-- Phase 2 fields
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS action_description TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS emotional_tone TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS technical_notes TEXT;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS sound_notes TEXT;

COMMENT ON COLUMN scenes.makeup IS 'Makeup and hair requirements (JSONB array)';
COMMENT ON COLUMN scenes.special_effects IS 'SFX/VFX requirements (JSONB array)';
COMMENT ON COLUMN scenes.vehicles IS 'Vehicles in scene (JSONB array)';
COMMENT ON COLUMN scenes.animals IS 'Animals in scene (JSONB array)';
COMMENT ON COLUMN scenes.extras IS 'Background actors/extras (JSONB array)';
COMMENT ON COLUMN scenes.stunts IS 'Stunt requirements (JSONB array)';
```

### Option B: Use Existing Fields
Leverage existing `description` and `dialogue` fields more extensively without schema changes. **Not recommended** - limits queryability and structure.

---

## Data Structure Examples

### Character Entry
```json
{
  "name": "SARAH",
  "role": "Lead",
  "dialogue_count": 15
}
```

### Prop Entry
```json
{
  "name": "Gun",
  "category": "weapon",
  "notes": "Glock 17, hero prop"
}
```

### Wardrobe Entry
```json
{
  "character": "SARAH",
  "items": ["Business suit", "High heels"],
  "notes": "Must match Scene 12"
}
```

### Makeup Entry (Proposed)
```json
{
  "character": "JOHN",
  "requirements": ["Bruised face", "Cut on forehead"],
  "notes": "Continuity from Scene 8"
}
```

### Special Effects Entry (Proposed)
```json
{
  "type": "practical",
  "effect": "Gunshot squib",
  "quantity": 3,
  "notes": "Chest hits"
}
```

---

## Current AI Analysis Coverage

The AI scene analysis currently extracts:
- ✅ Characters
- ✅ Props
- ✅ Wardrobe (basic)
- ✅ Description
- ✅ Dialogue excerpts
- ❌ Makeup (not extracted)
- ❌ Special effects (not extracted)
- ❌ Vehicles (not extracted)
- ❌ Animals (not extracted)
- ❌ Extras (not extracted)
- ❌ Stunts (not extracted)
- ❌ Emotional tone (not extracted)
- ❌ Technical notes (not extracted)

---

## Next Steps

1. **Create Migration** - Add missing JSONB columns to `scenes` table
2. **Update AI Prompts** - Enhance scene analysis to extract all breakdown categories
3. **Update `aggregate_scene_data()`** - Collect all new fields
4. **Update PDF Rendering** - Display all breakdown categories in reports
5. **Update Frontend** - Display new fields in SceneDetail component

---

## References
- Supabase Project: `twzfaizeyqwevmhjyicz`
- Migration Files: `backend/db/migrations/`
- Schema Client: `backend/db/supabase_client.py`
- Report Service: `backend/services/report_service.py`
