# Script Editing & Shooting Script Export Feature

## Executive Summary

This document outlines the design for handling script editing, revision tracking, and shooting script export in ScripDown AI. The approach focuses on **script management** rather than full text editing, positioning ScripDown as a production management tool that complements dedicated screenwriting software.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Design Philosophy](#design-philosophy)
3. [Feature Scope](#feature-scope)
4. [User Workflow](#user-workflow)
5. [Data Model](#data-model)
6. [API Endpoints](#api-endpoints)
7. [Frontend Components](#frontend-components)
8. [Implementation Phases](#implementation-phases)
9. [Technical Considerations](#technical-considerations)

---

## Problem Statement

Users need to:
1. Import a script (PDF) and create breakdowns ✅ *Already implemented*
2. Make changes to scene structure (reorder, split, merge, omit)
3. Track revisions when writers deliver updated drafts
4. Finalize and "lock" the script for production
5. Export a properly formatted **Shooting Script** PDF
6. Generate revision pages (colored pages) for day-of changes

---

## Design Philosophy

### Why Not Full Text Editing?

ScripDown is **not** competing with Final Draft, Highland, or WriterSolo. Writers use dedicated screenwriting tools for:
- Dialogue writing
- Action line formatting
- Automatic pagination
- Industry-standard FDX export

**ScripDown's value proposition:**
- AI-powered breakdown extraction
- Department collaboration (notes, tasks)
- Production scheduling (stripboard)
- Revision tracking across imported PDFs
- Shooting script generation with breakdown data

### The Right Approach: Structured Scene Management

Instead of a full text editor, ScripDown provides:
1. **Scene-level operations** (reorder, split, merge, omit)
2. **Metadata editing** (INT/EXT, setting, time of day)
3. **Revision import** (upload new PDF, auto-diff changes)
4. **Lock & finalize** (freeze scene numbers for production)
5. **Export engine** (generate formatted shooting script PDF)

---

## Feature Scope

### Core Features

| Feature | Description | Priority |
|---------|-------------|----------|
| Scene Reordering | Drag-and-drop to change scene order | P0 |
| Scene Splitting | Divide one scene into two (e.g., 12 → 12, 12A) | P0 |
| Scene Merging | Combine adjacent scenes | P1 |
| Scene Omission | Mark scene as OMITTED (preserves numbering) | P0 |
| Manual Scene Add | Create a new scene manually | P1 |
| Header Editing | Edit INT/EXT, setting, time of day | P0 |
| Revision Import | Upload new PDF, detect changes | P0 |
| Script Locking | Freeze scene numbers for shooting | P0 |
| Shooting Script Export | Generate formatted PDF | P0 |
| Revision Pages | Export colored pages for changes | P1 |

### Out of Scope (v1)

- Full dialogue/action text editing
- Real-time collaborative editing (Google Docs style)
- FDX import/export (Final Draft format)
- Automatic screenplay formatting

---

## User Workflow

### Phase 1: Import & Breakdown (Existing)

```
Upload PDF → Auto-detect scenes → AI analysis → Review breakdowns
```

### Phase 2: Working Draft (New)

```
Scene Manager View
├── Scene List (drag-and-drop reorderable)
├── Scene Detail Panel
│   ├── Header Editor (INT/EXT, Setting, Time)
│   ├── Scene Text (read-only display)
│   ├── Breakdown Cards (Characters, Props, etc.)
│   └── Department Notes
├── Actions Toolbar:
│   ├── Split Scene
│   ├── Merge with Next
│   ├── Omit Scene
│   └── Add New Scene
└── Import Revision Button
```

### Phase 3: Lock & Finalize (New)

```
Lock Script Wizard
├── Step 1: Review all scenes (confirm order)
├── Step 2: Assign locked scene numbers
├── Step 3: Set revision baseline (White pages)
└── Step 4: Generate Shooting Script PDF
```

### Phase 4: Post-Lock Revisions (New)

```
Revision Manager
├── Current Revision: Blue (Rev 2)
├── Changed Scenes: [12, 15, 22A]
├── Actions:
│   ├── Import New Revision PDF
│   ├── Mark Scene as Revised
│   └── Export Revision Pages
```

---

## Data Model

### New Tables

```sql
-- Script versions for revision tracking
CREATE TABLE script_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
  version_number INT NOT NULL,
  revision_color VARCHAR(20) DEFAULT 'white',
  -- Colors: white, blue, pink, yellow, green, goldenrod, buff, salmon, cherry
  pdf_path TEXT,
  imported_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT,
  is_locked BOOLEAN DEFAULT FALSE,
  locked_at TIMESTAMPTZ,
  locked_by UUID REFERENCES auth.users(id),
  UNIQUE(script_id, version_number)
);

-- Scene change history
CREATE TABLE scene_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scene_id UUID REFERENCES scenes(id) ON DELETE CASCADE,
  version_id UUID REFERENCES script_versions(id),
  change_type VARCHAR(20) NOT NULL,
  -- Types: created, modified, omitted, split, merged, reordered
  previous_data JSONB,
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  changed_by UUID REFERENCES auth.users(id)
);

-- Index for efficient history queries
CREATE INDEX idx_scene_history_scene ON scene_history(scene_id);
CREATE INDEX idx_scene_history_version ON scene_history(version_id);
```

### Schema Extensions (scenes table)

```sql
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS is_omitted BOOLEAN DEFAULT FALSE;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS omitted_at TIMESTAMPTZ;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS original_scene_number VARCHAR(10);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS locked_scene_number VARCHAR(10);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS revision_number INT DEFAULT 0;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS parent_scene_id UUID REFERENCES scenes(id);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS merged_into_scene_id UUID REFERENCES scenes(id);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS scene_order INT;
```

### Schema Extensions (scripts table)

```sql
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE;
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS current_revision_color VARCHAR(20) DEFAULT 'white';
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS current_version_id UUID REFERENCES script_versions(id);
```

---

## API Endpoints

### Scene Management

```
# Reorder scenes
PATCH  /api/scripts/:scriptId/scenes/reorder
Body: { scene_ids: ["uuid1", "uuid2", ...] }

# Split a scene
POST   /api/scripts/:scriptId/scenes/:sceneId/split
Body: { split_at_position: 1234, new_scene_suffix: "A" }

# Merge scenes
POST   /api/scripts/:scriptId/scenes/:sceneId/merge
Body: { merge_with_scene_id: "uuid" }

# Omit a scene
PATCH  /api/scripts/:scriptId/scenes/:sceneId/omit
Body: { is_omitted: true }

# Add manual scene
POST   /api/scripts/:scriptId/scenes/manual
Body: { int_ext: "INT", setting: "OFFICE", time_of_day: "DAY", ... }

# Update scene header
PATCH  /api/scripts/:scriptId/scenes/:sceneId
Body: { int_ext: "EXT", setting: "BEACH", time_of_day: "NIGHT" }
```

### Revision Management

```
# Import new revision
POST   /api/scripts/:scriptId/versions/import
Body: FormData with PDF file

# List versions
GET    /api/scripts/:scriptId/versions

# Get diff between versions
GET    /api/scripts/:scriptId/versions/:versionId/diff
Query: ?compare_to=<previous_version_id>

# Get version details
GET    /api/scripts/:scriptId/versions/:versionId
```

### Locking & Export

```
# Lock script (finalize)
POST   /api/scripts/:scriptId/lock
Body: { notes: "Locked for principal photography" }

# Unlock script (requires admin)
POST   /api/scripts/:scriptId/unlock

# Generate shooting script PDF
GET    /api/scripts/:scriptId/shooting-script
Query: ?format=pdf|html

# Export revision pages
GET    /api/scripts/:scriptId/revision-pages
Query: ?color=blue&format=pdf
```

---

## Frontend Components

### New Components

| Component | Location | Description |
|-----------|----------|-------------|
| `SceneManager.jsx` | `components/scenes/` | Main workspace for scene operations |
| `SceneReorderList.jsx` | `components/scenes/` | Drag-and-drop scene list |
| `SceneSplitModal.jsx` | `components/scenes/` | UI for splitting a scene |
| `SceneMergeModal.jsx` | `components/scenes/` | UI for merging scenes |
| `RevisionImportWizard.jsx` | `components/revisions/` | Upload and diff new PDF |
| `RevisionDiffView.jsx` | `components/revisions/` | Side-by-side diff display |
| `LockScriptWizard.jsx` | `components/finalize/` | Finalization flow |
| `ShootingScriptPreview.jsx` | `components/export/` | Preview before export |
| `RevisionPagesExport.jsx` | `components/export/` | Colored pages export |

### Modified Components

| Component | Changes |
|-----------|---------|
| `SceneViewer.jsx` | Add "Manage Scenes" button, link to SceneManager |
| `ScriptHeader.jsx` | Add lock status indicator, revision color badge |
| `Stripboard.jsx` | Integrate with locked scene numbers |

### New Routes

```javascript
// Scene Management
/scripts/:scriptId/manage          → SceneManager
/scripts/:scriptId/manage/split/:sceneId → SceneSplitModal (modal route)

// Revisions
/scripts/:scriptId/revisions       → RevisionList
/scripts/:scriptId/revisions/import → RevisionImportWizard
/scripts/:scriptId/revisions/:versionId/diff → RevisionDiffView

// Finalization
/scripts/:scriptId/finalize        → LockScriptWizard
/scripts/:scriptId/shooting-script → ShootingScriptPreview
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Database:**
- [ ] Create `script_versions` table
- [ ] Create `scene_history` table
- [ ] Add new columns to `scenes` table
- [ ] Add new columns to `scripts` table

**Backend:**
- [ ] Scene reorder endpoint
- [ ] Scene omit endpoint
- [ ] Basic version tracking on upload

**Frontend:**
- [ ] `SceneManager` component (read-only list with reorder)
- [ ] Omit scene UI

### Phase 2: Scene Operations (Week 3-4)

**Backend:**
- [ ] Scene split endpoint
- [ ] Scene merge endpoint
- [ ] Manual scene add endpoint
- [ ] Scene header update endpoint

**Frontend:**
- [ ] `SceneSplitModal`
- [ ] `SceneMergeModal`
- [ ] Add scene form
- [ ] Header editing in SceneDetail

### Phase 3: Revision Tracking (Week 5-6)

**Backend:**
- [ ] Revision import endpoint (PDF diff)
- [ ] Version comparison endpoint
- [ ] Scene change detection algorithm

**Frontend:**
- [ ] `RevisionImportWizard`
- [ ] `RevisionDiffView`
- [ ] Revision history timeline

### Phase 4: Lock & Export (Week 7-8)

**Backend:**
- [ ] Lock script endpoint
- [ ] Shooting script PDF generation
- [ ] Revision pages export

**Frontend:**
- [ ] `LockScriptWizard`
- [ ] `ShootingScriptPreview`
- [ ] `RevisionPagesExport`
- [ ] Lock status indicators throughout app

---

## Technical Considerations

### PDF Diff Algorithm

For detecting changes between revisions:

1. **Text-based diff**: Compare `full_text` of old vs new PDF
2. **Scene matching**: Match scenes by content hash or header similarity
3. **Change classification**:
   - `unchanged`: Content hash matches
   - `modified`: Header matches, content differs
   - `added`: No matching scene in previous version
   - `removed`: Scene exists in previous, not in new

```python
def diff_script_versions(old_version, new_version):
    old_scenes = get_scenes_by_version(old_version.id)
    new_scenes = get_scenes_by_version(new_version.id)
    
    changes = []
    for new_scene in new_scenes:
        match = find_matching_scene(new_scene, old_scenes)
        if not match:
            changes.append({'type': 'added', 'scene': new_scene})
        elif new_scene.content_hash != match.content_hash:
            changes.append({'type': 'modified', 'scene': new_scene, 'previous': match})
    
    for old_scene in old_scenes:
        if not find_matching_scene(old_scene, new_scenes):
            changes.append({'type': 'removed', 'scene': old_scene})
    
    return changes
```

### Shooting Script PDF Format

Industry-standard screenplay format:
- **Font**: Courier 12pt
- **Margins**: 1.5" left, 1" right, 1" top/bottom
- **Scene numbers**: Both margins, same line as header
- **Revision marks**: Asterisks (*) in right margin for changed lines
- **Page header**: Title, revision color, date

```html
<!-- WeasyPrint template structure -->
<style>
  @page {
    size: letter;
    margin: 1in 1in 1in 1.5in;
    @top-center { content: "SCRIPT TITLE - BLUE REVISION - 01/15/2025"; }
  }
  body { font-family: Courier, monospace; font-size: 12pt; }
  .scene-header { text-transform: uppercase; }
  .scene-number { position: absolute; left: -1.25in; }
  .revision-mark { position: absolute; right: -0.5in; }
</style>
```

### Scene Numbering Rules

When script is locked:
1. Scene numbers become immutable
2. New scenes get letter suffixes (12A, 12B)
3. Omitted scenes show "OMITTED" but keep number
4. Split scenes: 12 → 12, 12A
5. Merged scenes: 12, 13 → 12 (13 marked OMITTED)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to lock script | < 5 minutes |
| Revision import accuracy | > 95% scene matching |
| PDF export quality | Industry-standard format |
| User satisfaction | > 4.5/5 rating |

---

## Open Questions

1. **Collaborative editing**: Should multiple users edit simultaneously? (Deferred to v2)
2. **FDX support**: Import/export Final Draft format? (Deferred to v2)
3. **Offline support**: Edit scenes without internet? (Deferred to v2)
4. **Mobile**: Scene management on tablet? (Consider for v1.5)

---

## Appendix: Revision Color Sequence

Industry-standard revision page colors:

| Order | Color | Hex Code |
|-------|-------|----------|
| 1 | White | #FFFFFF |
| 2 | Blue | #ADD8E6 |
| 3 | Pink | #FFB6C1 |
| 4 | Yellow | #FFFF99 |
| 5 | Green | #90EE90 |
| 6 | Goldenrod | #DAA520 |
| 7 | Buff | #F0DC82 |
| 8 | Salmon | #FA8072 |
| 9 | Cherry | #DE3163 |
| 10+ | Double White, Double Blue, etc. |

---

*Document created: 2025-01-09*
*Last updated: 2025-01-09*
*Status: BRAINSTORM / READY FOR REVIEW*
