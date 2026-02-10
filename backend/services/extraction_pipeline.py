"""
Extraction Pipeline v2 - Page-Based Two-Pass Architecture

This module implements a robust, resumable, and accurate script extraction system.

ARCHITECTURE:
============

Phase 1: UPLOAD (Synchronous, Fast)
-----------------------------------
1. Parse PDF → Extract text PER PAGE with page numbers
2. Store pages in script_pages table (with content hash for idempotency)
3. Quick regex scan to detect scene headers
4. Create scene_candidates with page ranges
5. Return script_id immediately to user

Phase 2: ANALYSIS (Background, Resumable)
-----------------------------------------
1. For each scene_candidate:
   - Extract scene text from relevant pages
   - AI enhances: characters, props, wardrobe, etc.
   - Store with original scene number + page range
   
2. Post-processing jobs:
   - Character analysis (aggregates all scenes per character)
   - Location analysis (aggregates all scenes per location)
   - Story arc analysis (samples key scenes)

KEY FEATURES:
- Idempotent: Content hashing prevents duplicate processing
- Resumable: Failed scenes can be retried independently
- Accurate: Scene numbers come from script, not AI invention
- Page-aware: Every scene knows its exact page range
"""

import re
import hashlib
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ExtractionStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PageData:
    """Represents a single page from the script."""
    page_number: int
    text: str
    content_hash: str
    has_scene_header: bool = False
    scene_headers: List[Dict] = None
    
    def __post_init__(self):
        if self.scene_headers is None:
            self.scene_headers = []


@dataclass
class SceneCandidate:
    """A detected scene before AI enhancement."""
    scene_number_original: str  # "42", "42A", etc.
    scene_order: int            # Sequential order for sorting
    int_ext: str                # INT, EXT, INT/EXT
    setting: str                # Location name
    time_of_day: str            # DAY, NIGHT, DUSK, etc.
    page_start: int
    page_end: int
    text_start: int             # Character position in full text
    text_end: int
    content_hash: str           # For idempotency
    status: ExtractionStatus = ExtractionStatus.PENDING
    # ScreenPy enrichments (Phase 1)
    location_hierarchy: List = None
    speakers: Dict = None
    shot_type: str = None
    transitions: List = None
    parse_method: str = "regex"

    def __post_init__(self):
        if self.location_hierarchy is None:
            self.location_hierarchy = []
        if self.speakers is None:
            self.speakers = {}
        if self.transitions is None:
            self.transitions = []


# ============================================
# Scene Header Detection (Regex-based)
# ============================================

# Standard screenplay scene header patterns
# Time of day options - comprehensive list
TIME_OF_DAY = r"(DAY|NIGHT|DUSK|DAWN|MORNING|EVENING|AFTERNOON|CONTINUOUS|LATER|SAME|MOMENT'?S?\s*LATER|MOMENTS?\s*LATER)"

SCENE_HEADER_PATTERNS = [
    # Pattern 1: "42. INT. COFFEE SHOP - DAY" (standard numbered + TOD)
    rf'^(\d+[A-Z]?)\.\s*(INT|EXT|INT\.?/EXT|EXT\.?/INT|I/E|E/I)[.\s]+(.+?)\s*[-–—]\s*{TIME_OF_DAY}',

    # Pattern 2: "42. INT. COFFEE SHOP" (numbered + optional TOD)
    r'^(\d+[A-Z]?)\.\s*(INT|EXT|INT\.?/EXT|EXT\.?/INT|I/E|E/I)[.\s]+(.+?)(?:\s*[-–—]\s*(.+?))?$',

    # Pattern 3: "SCENE 42 - INT. COFFEE SHOP - DAY"
    rf'^SCENE\s+(\d+[A-Z]?)\s*[-–—:]\s*(INT|EXT|INT\.?/EXT|EXT\.?/INT)[.\s]+(.+?)\s*[-–—]\s*{TIME_OF_DAY}',

    # Pattern 4: "42 INT. COFFEE SHOP - DAY" (FDX no period + TOD)
    rf'^(\d+[A-Z]?)\s+(INT|EXT|INT\.?/EXT|EXT\.?/INT|I/E|E/I)[.\s]+(.+?)\s*[-–—]\s*{TIME_OF_DAY}',

    # Pattern 5: "INT. COFFEE SHOP - DAY" (no scene number + TOD)
    rf'^()(INT|EXT|INT\.?/EXT|EXT\.?/INT|I/E|E/I)[.\s]+(.+?)\s*[-–—]\s*{TIME_OF_DAY}',

    # Pattern 6: "A1 INT. COFFEE SHOP - DAY" (alpha-prefix scene number, e.g. revision scenes)
    rf'^([A-Z]\d+[A-Z]?)\.?\s+(INT|EXT|INT\.?/EXT|EXT\.?/INT|I/E|E/I)[.\s]+(.+?)\s*[-–—]\s*{TIME_OF_DAY}',

    # Pattern 7: "FLASHBACK - INT. COFFEE SHOP - DAY" / "DREAM SEQUENCE - EXT. PARK - NIGHT"
    rf'^(?:FLASHBACK|DREAM SEQUENCE)\s*[-–—:]\s*()(INT|EXT|INT\.?/EXT|EXT\.?/INT|I/E|E/I)[.\s]+(.+?)\s*[-–—]\s*{TIME_OF_DAY}',

    # Pattern 8: "42 INT. COFFEE SHOP" (FDX no period, no TOD)
    r'^(\d+[A-Z]?)\s+(INT|EXT|INT\.?/EXT|EXT\.?/INT|I/E|E/I)[.\s]+(.+?)()$',

    # Pattern 9: "INT. COFFEE SHOP" (no scene number, no TOD — catch-all)
    r'^()(INT|EXT|INT\.?/EXT|EXT\.?/INT|I/E|E/I)[.\s]+(.+?)()$',
]


def compute_content_hash(text: str) -> str:
    """Generate a hash for content deduplication."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]


def detect_scene_headers(text: str, page_number: int = None) -> List[Dict]:
    """
    Detect all scene headers in text using regex patterns.
    
    Returns list of dicts with:
    - scene_number: Original scene number from script
    - int_ext: INT/EXT designation
    - setting: Location name
    - time_of_day: DAY/NIGHT/etc
    - position: Character position in text
    - line: The full header line
    - page_number: If provided
    """
    headers = []
    
    for line_num, line in enumerate(text.split('\n')):
        line_stripped = line.strip()
        
        for pattern in SCENE_HEADER_PATTERNS:
            match = re.match(pattern, line_stripped, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Safely extract values (some may be None)
                scene_num = groups[0] if groups[0] else None
                int_ext = groups[1].upper().replace('.', '') if groups[1] else 'INT'
                setting = groups[2].strip() if groups[2] else ''
                time_of_day = groups[3].upper() if len(groups) > 3 and groups[3] else 'DAY'
                
                # Skip if no valid setting found
                if not setting:
                    continue
                
                header = {
                    'scene_number': scene_num,
                    'int_ext': int_ext,
                    'setting': setting,
                    'time_of_day': time_of_day,
                    'position': text.find(line),
                    'line': line_stripped,
                    'line_number': line_num,
                }
                
                if page_number is not None:
                    header['page_number'] = page_number
                
                headers.append(header)
                break  # Only match first pattern
    
    return headers


def assign_scene_numbers(headers: List[Dict]) -> List[Dict]:
    """
    Assign scene numbers to headers that don't have them.
    Uses sequential numbering based on position.
    """
    current_number = 1
    
    for header in headers:
        if header['scene_number']:
            # Try to extract numeric part for continuation
            num_match = re.match(r'(\d+)', header['scene_number'])
            if num_match:
                current_number = int(num_match.group(1)) + 1
        else:
            # Assign sequential number
            header['scene_number'] = str(current_number)
            header['scene_number_inferred'] = True
            current_number += 1
    
    return headers


# ============================================
# Page-Based PDF Parsing
# ============================================

def parse_pdf_with_pages(file_path: str) -> Tuple[List[PageData], str]:
    """
    Parse PDF and extract text per page with metadata.
    
    Uses pdfplumber (replaces PyPDF2) for better text quality.
    Raw text (layout=False) is used here for page storage and
    regex header detection. The grammar path uses layout=True
    via the screenplay_parser adapter.
    
    Returns:
    - List of PageData objects
    - Full concatenated text
    """
    import pdfplumber
    
    pages = []
    full_text = ""
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                
                # Detect scene headers on this page
                headers = detect_scene_headers(page_text, page_num)
                
                page_data = PageData(
                    page_number=page_num,
                    text=page_text,
                    content_hash=compute_content_hash(page_text),
                    has_scene_header=len(headers) > 0,
                    scene_headers=headers
                )
                
                pages.append(page_data)
                full_text += page_text + "\n"
                
    except Exception as e:
        raise Exception(f"Error parsing PDF: {str(e)}")
    
    return pages, full_text


def build_scene_candidates(pages: List[PageData], full_text: str) -> List[SceneCandidate]:
    """
    Build scene candidates from detected headers across all pages.
    
    Each candidate includes:
    - Original scene number from script
    - Page range (start to end)
    - Text boundaries
    """
    # Calculate page offsets in full text
    page_offsets = {}
    current_offset = 0
    for page in pages:
        page_offsets[page.page_number] = current_offset
        current_offset += len(page.text) + 1  # +1 for the newline we add
    
    # Collect all headers with their page info and GLOBAL position
    all_headers = []
    for page in pages:
        page_offset = page_offsets[page.page_number]
        for header in page.scene_headers:
            header['page_number'] = page.page_number
            # Convert page-relative position to global position
            header['global_position'] = page_offset + header['position']
            all_headers.append(header)
    
    # Sort by global position in full text
    all_headers.sort(key=lambda h: h['global_position'])
    
    # Assign scene numbers to headers without them
    all_headers = assign_scene_numbers(all_headers)
    
    # Build candidates with text boundaries
    candidates = []
    
    for i, header in enumerate(all_headers):
        # Text starts at this header (use global position)
        text_start = header['global_position']
        
        # Text ends at next header or end of document
        if i + 1 < len(all_headers):
            text_end = all_headers[i + 1]['global_position']
        else:
            text_end = len(full_text)
        
        # Find page range
        page_start = header['page_number']
        page_end = page_start
        
        # Check if scene spans multiple pages
        scene_text = full_text[text_start:text_end]
        for page in pages:
            if page.page_number > page_start:
                # Check if any of this page's text is in the scene
                if page.text and page.text[:100] in scene_text:
                    page_end = page.page_number
        
        candidate = SceneCandidate(
            scene_number_original=header['scene_number'],
            scene_order=i + 1,
            int_ext=header['int_ext'],
            setting=header['setting'],
            time_of_day=header['time_of_day'],
            page_start=page_start,
            page_end=page_end,
            text_start=text_start,
            text_end=text_end,
            content_hash=compute_content_hash(scene_text),
        )
        
        candidates.append(candidate)
    
    return candidates


# ============================================
# Database Operations
# ============================================

def save_pages_to_db(script_id: int, pages: List[PageData], db_conn) -> int:
    """
    Save parsed pages to database.
    Returns number of pages saved.
    """
    cursor = db_conn.cursor()
    
    saved = 0
    for page in pages:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO script_pages 
                (script_id, page_number, page_text, content_hash, has_scene_header, scene_headers_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                script_id,
                page.page_number,
                page.text,
                page.content_hash,
                page.has_scene_header,
                json.dumps(page.scene_headers)
            ))
            saved += 1
        except Exception as e:
            print(f"Error saving page {page.page_number}: {e}")
    
    db_conn.commit()
    return saved


def save_scene_candidates_to_db(script_id: int, candidates: List[SceneCandidate], db_conn) -> int:
    """
    Save scene candidates to database for processing.
    Includes ScreenPy enrichment columns (Phase 1).
    Returns number of candidates saved.
    """
    cursor = db_conn.cursor()
    
    saved = 0
    for candidate in candidates:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO scene_candidates 
                (script_id, scene_number_original, scene_order, int_ext, setting, 
                 time_of_day, page_start, page_end, text_start, text_end, 
                 content_hash, status,
                 location_hierarchy, speaker_list, shot_type, transitions, parse_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                script_id,
                candidate.scene_number_original,
                candidate.scene_order,
                candidate.int_ext,
                candidate.setting,
                candidate.time_of_day,
                candidate.page_start,
                candidate.page_end,
                candidate.text_start,
                candidate.text_end,
                candidate.content_hash,
                candidate.status.value,
                json.dumps(candidate.location_hierarchy),
                json.dumps(candidate.speakers),
                candidate.shot_type,
                json.dumps(candidate.transitions),
                candidate.parse_method,
            ))
            saved += 1
        except Exception as e:
            print(f"Error saving candidate {candidate.scene_number_original}: {e}")
    
    db_conn.commit()
    return saved


def get_pending_candidates(script_id: int, db_conn) -> List[Dict]:
    """Get scene candidates that haven't been processed yet.
    
    Includes ScreenPy enrichment columns (Phase 1) so that Phase 2
    AI prompt optimization can use pre-extracted speakers, shot_type,
    and location_hierarchy.
    """
    cursor = db_conn.cursor()
    
    cursor.execute("""
        SELECT candidate_id, scene_number_original, scene_order, int_ext, setting,
               time_of_day, page_start, page_end, text_start, text_end, content_hash,
               speaker_list, shot_type, location_hierarchy, parse_method
        FROM scene_candidates
        WHERE script_id = ? AND status = 'pending'
        ORDER BY scene_order
    """, (script_id,))
    
    candidates = []
    for row in cursor.fetchall():
        candidates.append({
            'candidate_id': row[0],
            'scene_number_original': row[1],
            'scene_order': row[2],
            'int_ext': row[3],
            'setting': row[4],
            'time_of_day': row[5],
            'page_start': row[6],
            'page_end': row[7],
            'text_start': row[8],
            'text_end': row[9],
            'content_hash': row[10],
            'speaker_list': row[11],
            'shot_type': row[12],
            'location_hierarchy': row[13],
            'parse_method': row[14],
        })
    
    return candidates


def check_already_processed(script_id: int, content_hash: str, db_conn) -> bool:
    """Check if a scene with this content hash already exists."""
    cursor = db_conn.cursor()
    
    cursor.execute("""
        SELECT scene_id FROM scenes 
        WHERE script_id = ? AND content_hash = ?
    """, (script_id, content_hash))
    
    return cursor.fetchone() is not None


# ============================================
# Main Pipeline Entry Points
# ============================================

def process_upload(file_path: str, script_id: int, db_conn, locale_codes=None) -> Dict:
    """
    Phase 1: Process uploaded script.
    
    Architecture (grammar-first with regex fallback):
    1. Parse PDF with pdfplumber (page awareness)
    2. Run ScreenPy grammar parser on normalized layout text
    3. Fall back to regex on raw text if grammar returns 0 scenes
    4. Save pages and enriched scene candidates to database
    
    Returns summary of what was found.
    """
    print(f"[Pipeline] Processing upload for script {script_id}")
    
    # Step 1: Parse PDF for page storage (raw text, pdfplumber)
    pages, full_text = parse_pdf_with_pages(file_path)
    print(f"[Pipeline] Parsed {len(pages)} pages")
    
    # Save pages to DB
    pages_saved = save_pages_to_db(script_id, pages, db_conn)
    print(f"[Pipeline] Saved {pages_saved} pages to database")
    
    # Step 2: Run grammar-first parser adapter
    try:
        from services.screenplay_parser import parse_screenplay
        
        parsed_scenes, parse_meta = parse_screenplay(
            file_path, locale_codes=locale_codes
        )
        
        parse_method = parse_meta.get("parse_method", "grammar")
        print(f"[Pipeline] {parse_method} parser found {len(parsed_scenes)} scenes")
        
        # Convert ParsedScene objects to SceneCandidate objects
        candidates = []
        for ps in parsed_scenes:
            candidates.append(SceneCandidate(
                scene_number_original=ps.scene_number_original,
                scene_order=ps.scene_order,
                int_ext=ps.int_ext,
                setting=ps.setting,
                time_of_day=ps.time_of_day,
                page_start=ps.page_start,
                page_end=ps.page_end,
                text_start=ps.text_start,
                text_end=ps.text_end,
                content_hash=ps.content_hash,
                location_hierarchy=ps.location_hierarchy,
                speakers=ps.speakers,
                shot_type=ps.shot_type,
                transitions=ps.transitions,
                parse_method=ps.parse_method,
            ))
    except Exception as e:
        # If the grammar adapter fails entirely, fall back to legacy regex
        print(f"[Pipeline] Grammar adapter error: {e}, using legacy regex")
        candidates = build_scene_candidates(pages, full_text)
        parse_meta = {"parse_method": "regex", "error": str(e)}
    
    print(f"[Pipeline] Found {len(candidates)} scene candidates")
    
    # Save candidates (with enrichment columns)
    candidates_saved = save_scene_candidates_to_db(script_id, candidates, db_conn)
    print(f"[Pipeline] Saved {candidates_saved} candidates to database")
    
    return {
        'script_id': script_id,
        'total_pages': len(pages),
        'scene_candidates': len(candidates),
        'parse_method': parse_meta.get('parse_method', 'regex'),
        'status': 'ready_for_analysis',
        **{k: v for k, v in parse_meta.items() if k != 'parse_method'},
    }


def get_scene_text(script_id: int, text_start: int, text_end: int, db_conn) -> str:
    """Get the text for a specific scene from stored pages."""
    cursor = db_conn.cursor()
    
    cursor.execute("""
        SELECT script_text FROM scripts WHERE script_id = ?
    """, (script_id,))
    
    row = cursor.fetchone()
    if row:
        return row[0][text_start:text_end]
    return ""


# ============================================
# Schema Migration
# ============================================

SCHEMA_MIGRATION = """
-- New table for storing pages
CREATE TABLE IF NOT EXISTS script_pages (
    page_id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    page_text TEXT,
    content_hash TEXT,
    has_scene_header BOOLEAN DEFAULT FALSE,
    scene_headers_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(script_id, page_number),
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE
);

-- New table for scene candidates (pre-AI)
CREATE TABLE IF NOT EXISTS scene_candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    scene_number_original TEXT,
    scene_order INTEGER,
    int_ext TEXT,
    setting TEXT,
    time_of_day TEXT,
    page_start INTEGER,
    page_end INTEGER,
    text_start INTEGER,
    text_end INTEGER,
    content_hash TEXT,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    -- ScreenPy enrichment columns (Phase 1)
    location_hierarchy TEXT DEFAULT '[]',
    speaker_list TEXT DEFAULT '{}',
    shot_type TEXT,
    transitions TEXT DEFAULT '[]',
    parse_method TEXT DEFAULT 'regex',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE
);

-- Add content_hash to scenes table if not exists
-- ALTER TABLE scenes ADD COLUMN content_hash TEXT;

-- Index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_scene_candidates_status 
ON scene_candidates(script_id, status);

CREATE INDEX IF NOT EXISTS idx_script_pages_script 
ON script_pages(script_id, page_number);
"""


def run_migration(db_conn):
    """Run schema migration for new tables."""
    cursor = db_conn.cursor()
    
    for statement in SCHEMA_MIGRATION.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                cursor.execute(statement)
            except Exception as e:
                print(f"Migration warning: {e}")
    
    db_conn.commit()
    print("[Pipeline] Schema migration complete")
