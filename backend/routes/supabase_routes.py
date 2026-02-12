"""
Supabase-based API Routes for SlateOne (ScripDown AI)

This module provides REST endpoints backed by Supabase instead of SQLite.
All IDs are UUIDs and data is stored in Supabase PostgreSQL.
"""

import os
import re
import json
import uuid
import time
import threading
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# Auth middleware
from middleware.auth import require_auth, optional_auth, get_user_id, get_current_user

# Supabase client
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '').strip()
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '').strip()

# Use service key for server-side operations (bypasses RLS)
# Fall back to anon key if service key not set
supabase_key = SUPABASE_SERVICE_KEY if SUPABASE_SERVICE_KEY else SUPABASE_ANON_KEY

supabase = None
if not SUPABASE_URL or not supabase_key:
    print("WARNING: Supabase credentials not configured")
else:
    try:
        supabase = create_client(SUPABASE_URL, supabase_key)
        print(f"✓ Supabase connected: {SUPABASE_URL}")
    except Exception as e:
        print(f"ERROR: Failed to connect to Supabase: {e}")

supabase_bp = Blueprint('supabase', __name__)

# Temporary user ID for development (no auth yet)
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


def ensure_dev_user():
    """Ensure development user exists in profiles table."""
    if not supabase:
        return
    try:
        # Check if user exists
        result = supabase.table('profiles').select('id').eq('id', DEV_USER_ID).execute()
        if not result.data:
            # Create dev user (this may fail due to FK constraint with auth.users)
            # For now, we'll handle this gracefully
            pass
    except Exception as e:
        print(f"Dev user check: {e}")


# ============================================
# Scripts Endpoints
# ============================================

@supabase_bp.route('/api/scripts', methods=['GET'])
@optional_auth
def get_scripts():
    """Get all scripts for the current user (owned + team member)."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        user_id = get_user_id()
        
        script_ids = set()
        owned_scripts = {}
        member_scripts = {}
        
        if user_id:
            # Get scripts owned by user
            owned_result = supabase.table('scripts').select('*').eq('user_id', user_id).execute()
            for script in owned_result.data or []:
                script_ids.add(script['id'])
                owned_scripts[script['id']] = script
            
            # Get scripts where user is a team member
            member_result = supabase.table('script_members').select('script_id, department_code, role').eq('user_id', user_id).execute()
            member_script_ids = [m['script_id'] for m in (member_result.data or [])]
            
            if member_script_ids:
                # Fetch those scripts
                for script_id in member_script_ids:
                    if script_id not in script_ids:
                        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
                        if script_result.data:
                            script_ids.add(script_id)
                            member_scripts[script_id] = {
                                'script': script_result.data,
                                'membership': next((m for m in member_result.data if m['script_id'] == script_id), None)
                            }
            
            # Also include scripts with no owner (legacy)
            legacy_result = supabase.table('scripts').select('*').is_('user_id', 'null').execute()
            for script in legacy_result.data or []:
                if script['id'] not in script_ids:
                    script_ids.add(script['id'])
                    owned_scripts[script['id']] = script
        else:
            # No auth - just get legacy scripts
            legacy_result = supabase.table('scripts').select('*').is_('user_id', 'null').execute()
            for script in legacy_result.data or []:
                owned_scripts[script['id']] = script
        
        scripts = []
        
        # Process owned scripts
        for script_id, script in owned_scripts.items():
            scene_result = supabase.table('scenes').select('id, analysis_status').eq('script_id', script['id']).execute()
            total_scenes = len(scene_result.data) if scene_result.data else 0
            analyzed_scenes = sum(1 for s in (scene_result.data or []) if s.get('analysis_status') == 'complete')
            
            scripts.append({
                'script_id': script['id'],
                'id': script['id'],
                'script_name': script['title'],
                'title': script['title'],
                'writer_name': script.get('writer_name'),
                'upload_date': script['created_at'],
                'created_at': script['created_at'],
                'total_pages': script.get('total_pages', 0),
                'scene_count': total_scenes,
                'analyzed_scenes': analyzed_scenes,
                'analysis_status': script.get('analysis_status', 'pending'),
                'is_owner': True,
                'membership': None
            })
        
        # Process member scripts
        for script_id, data in member_scripts.items():
            script = data['script']
            membership = data['membership']
            
            scene_result = supabase.table('scenes').select('id, analysis_status').eq('script_id', script['id']).execute()
            total_scenes = len(scene_result.data) if scene_result.data else 0
            analyzed_scenes = sum(1 for s in (scene_result.data or []) if s.get('analysis_status') == 'complete')
            
            scripts.append({
                'script_id': script['id'],
                'id': script['id'],
                'script_name': script['title'],
                'title': script['title'],
                'writer_name': script.get('writer_name'),
                'upload_date': script['created_at'],
                'created_at': script['created_at'],
                'total_pages': script.get('total_pages', 0),
                'scene_count': total_scenes,
                'analyzed_scenes': analyzed_scenes,
                'analysis_status': script.get('analysis_status', 'pending'),
                'is_owner': False,
                'membership': {
                    'department_code': membership['department_code'] if membership else None,
                    'role': membership['role'] if membership else None
                }
            })
        
        # Sort by created_at descending
        scripts.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'scripts': scripts}), 200
        
    except Exception as e:
        print(f"Error getting scripts: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>', methods=['GET'])
def get_script(script_id):
    """Get a single script by ID."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        return jsonify(result.data), 200
    except Exception as e:
        print(f"Error getting script: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>', methods=['DELETE'])
def delete_script(script_id):
    """Delete a script and all related data including Storage files."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # 1. Get file path before deleting record
        script_result = supabase.table('scripts').select('file_path').eq('id', script_id).single().execute()
        file_path = script_result.data.get('file_path') if script_result.data else None
        
        # 2. Delete from database (cascades to scenes, pages, etc.)
        supabase.table('scripts').delete().eq('id', script_id).execute()
        print(f"✓ Script deleted from database: {script_id}")
        
        # 3. Delete PDF from Supabase Storage
        if file_path:
            try:
                supabase.storage.from_('scripts').remove([file_path])
                print(f"✓ PDF deleted from Storage: {file_path}")
            except Exception as storage_err:
                print(f"Warning: Could not delete from Storage: {storage_err}")
                # Don't fail the request if storage delete fails
        
        return jsonify({'message': 'Script deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting script: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>', methods=['PATCH'])
@optional_auth
def update_script(script_id):
    """Update script metadata (title, writer_name, etc.)."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Only allow updating specific fields
        allowed_fields = {'title', 'writer_name', 'genre', 'logline', 'draft_version'}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        supabase.table('scripts').update(update_data).eq('id', script_id).execute()
        
        return jsonify({'message': 'Script updated', 'updated': update_data}), 200
        
    except Exception as e:
        print(f"Error updating script: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/metadata', methods=['GET'])
def get_script_metadata(script_id):
    """Get script metadata."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('scripts').select(
            'id, title, writer_name, draft_version, genre, logline, total_pages, created_at, analysis_status'
        ).eq('id', script_id).single().execute()
        
        return jsonify(result.data), 200
    except Exception as e:
        print(f"Error getting script metadata: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# Upload Endpoint
# ============================================

@supabase_bp.route('/api/upload', methods=['POST'])
@optional_auth
def upload_script():
    """
    Upload a script to Supabase.
    
    Architecture (Phase 1 — ScreenPy integration):
    1. Save PDF to temp file
    2. Extract text via pdfplumber (replaces PyMuPDF)
    3. Upload PDF to Supabase Storage
    4. Create script + page records
    5. Run grammar-first scene detection (falls back to regex)
    6. Write enriched scenes + scene_candidates to Supabase
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        import tempfile
        import pdfplumber
        
        # Read file content
        file_content = file.read()
        filename = secure_filename(file.filename)
        
        # Save to temp file (pdfplumber needs a file path)
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.pdf')
        try:
            os.write(tmp_fd, file_content)
            os.close(tmp_fd)
            
            # Generate UUID for script
            script_id = str(uuid.uuid4())
            
            # Upload original PDF to Supabase Storage
            storage_path = f"{script_id}/{filename}"
            try:
                supabase.storage.from_('scripts').upload(
                    storage_path,
                    file_content,
                    {'content-type': 'application/pdf'}
                )
                print(f"✓ PDF uploaded to Storage: {storage_path}")
            except Exception as storage_error:
                print(f"Warning: Storage upload failed: {storage_error}")
            
            # Extract text via pdfplumber (replaces PyMuPDF)
            pages_data = []
            full_text_parts = []
            
            with pdfplumber.open(tmp_path) as pdf:
                total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    pages_data.append({
                        'page_number': page_num,
                        'text': text
                    })
                    full_text_parts.append(text)
            
            full_text = '\n\n'.join(full_text_parts)
            
            # Extract comprehensive metadata from title page
            title_page_text = pages_data[0]['text'] if pages_data else full_text[:4000]
            metadata = extract_title_page_metadata(title_page_text)
            
            raw_title = metadata.get('title')
            # Safety check: reject titles that look like scene headings after .title() conversion
            if raw_title and re.match(r'^(Int[\./]|Ext[\./]|Int/Ext)', raw_title, re.IGNORECASE):
                raw_title = None
            title = raw_title or (filename.rsplit('.', 1)[0] if '.' in filename else filename)
            writer_name = metadata.get('writers')
            
            print(f"✓ Extracted metadata: {metadata}")
            
            # Get user ID from auth token
            user_id = get_user_id()
            
            # Create script record
            script_data = {
                'id': script_id,
                'user_id': user_id,
                'title': title,
                'writer_name': writer_name,
                'file_name': filename,
                'file_path': storage_path,
                'file_size': len(file_content),
                'full_text': full_text,
                'total_pages': total_pages,
                'analysis_status': 'pending',
                'draft_version': metadata.get('draft_version'),
                'genre': None,
                'logline': metadata.get('based_on'),
                'production_company': metadata.get('production_company'),
                'contact_phone': metadata.get('phone'),
                'contact_email': metadata.get('email'),
                'contact_address': metadata.get('address'),
                'based_on': metadata.get('based_on'),
                'copyright_year': metadata.get('copyright'),
                'wga_registration': metadata.get('wga_registration'),
            }
            
            supabase.table('scripts').insert(script_data).execute()
            print(f"✓ Script saved to Supabase: {script_id}")
            
            # Create page records (batch insert for performance)
            page_records = [
                {
                    'script_id': script_id,
                    'page_number': page['page_number'],
                    'page_text': page['text']
                }
                for page in pages_data
            ]
            # Supabase supports batch insert — send all pages in one request
            # Chunk into batches of 50 to avoid payload size limits
            BATCH_SIZE = 50
            for i in range(0, len(page_records), BATCH_SIZE):
                batch = page_records[i:i + BATCH_SIZE]
                supabase.table('script_pages').insert(batch).execute()
            
            # Run grammar-first scene detection with regex fallback
            scenes_detected, parse_meta = detect_and_create_scenes_v2(
                script_id, tmp_path, full_text, pages_data
            )
            
            return jsonify({
                'message': 'Script uploaded successfully',
                'script_id': script_id,
                'total_pages': total_pages,
                'scene_candidates': scenes_detected,
                'parse_method': parse_meta.get('parse_method', 'regex'),
                'status': 'ready_for_analysis'
            }), 201
            
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        
    except Exception as e:
        print(f"Error uploading script: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def extract_title_page_metadata(first_page_text):
    """
    Extract comprehensive metadata from script title page.
    
    Returns dict with:
    - title, writers, based_on, production_company
    - address, city, country, phone, email
    - agent_name, agent_company, agent_contact
    - draft_version, draft_date, copyright
    """
    import re
    
    text = first_page_text[:4000]  # Title page is usually first 4000 chars
    metadata = {}
    
    # 1. TITLE - Usually centered, often underlined or in caps at top
    # Exclude scene headings (INT./EXT.), common non-title keywords, and page numbering
    title_exclude_words = [
        'WRITTEN', 'BY', 'BASED', 'DRAFT', 'FADE IN', 'FADE OUT',
        'CUT TO', 'DISSOLVE', 'CONTINUED', 'CONT\'D', 'MORE',
        'PRODUCTIONS', 'PICTURES', 'ENTERTAINMENT', 'FILMS',
    ]
    scene_heading_re = re.compile(r'^(INT[\./]|EXT[\./]|INT/EXT|I/E[\.\s])', re.IGNORECASE)
    time_of_day_re = re.compile(r'\b(DAY|NIGHT|DAWN|DUSK|EVENING|MORNING|CONTINUOUS|LATER|SAME TIME)\b', re.IGNORECASE)
    
    lines = text.split('\n')
    for line in lines[:20]:  # Title usually in first 20 lines
        line = line.strip()
        if len(line) > 2 and len(line) < 60 and line.isupper():
            # Skip scene headings
            if scene_heading_re.match(line):
                continue
            # Skip lines with time-of-day markers (scene headings)
            if time_of_day_re.search(line):
                continue
            # Skip common non-title words
            if any(x in line for x in title_exclude_words):
                continue
            # Skip lines that look like page numbers or single short words
            if len(line) <= 3 or line.isdigit():
                continue
            metadata['title'] = line.title()
            break
    
    # 2. WRITERS - After "Written by", "Screenplay by", or just "By"
    writer_patterns = [
        r'(?:written\s+by|screenplay\s+by)\s*\n?\s*([A-Za-z][A-Za-z\s\&\,\.]+?)(?:\n|$)',
        r'(?:WRITTEN\s+BY|SCREENPLAY\s+BY)\s*\n?\s*([A-Za-z][A-Za-z\s\&\,\.]+?)(?:\n|$)',
        r'^By\s*\n+\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*$',  # "By" on one line, name on next
    ]
    for pattern in writer_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            metadata['writers'] = match.group(1).strip()
            break
    
    # Fallback: Look for "By" followed by name on next line
    if 'writers' not in metadata:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for i, line in enumerate(lines):
            if line.lower() == 'by' and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Check if next line looks like a name (1-4 capitalized words)
                # Allow single names (Madonna, Prince) and names with Jr./Sr./III
                words = next_line.split()
                if 1 <= len(words) <= 5:
                    # Filter out common non-name words
                    non_names = ['the', 'a', 'an', 'and', 'or', 'for', 'of', 'in', 'on', 'at']
                    if words[0].lower() not in non_names and words[0][0].isupper():
                        metadata['writers'] = next_line
                        break
    
    # 3. BASED ON - Source material
    based_on_pattern = r'(?:based\s+on\s+(?:the\s+)?(?:book|novel|story|play)?)\s*\n?\s*([^\n]+)'
    match = re.search(based_on_pattern, text, re.IGNORECASE)
    if match:
        metadata['based_on'] = match.group(1).strip()
    
    # 4. PRODUCTION COMPANY - Usually all caps, bottom of page
    company_patterns = [
        r'^([A-Z][A-Z\s]+(?:PRODUCTIONS?|FILMS?|ENTERTAINMENT|STUDIOS?|PICTURES))\s*$',
        r'^([A-Z][A-Z\s]+(?:PROD\.?|ENT\.?))\s*$',
    ]
    for pattern in company_patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            metadata['production_company'] = match.group(1).strip()
            break
    
    # 5. ADDRESS - Street address pattern
    address_pattern = r'(\d+\s+[A-Za-z][A-Za-z\s\.]+(?:rd|st|ave|street|road|drive|lane|blvd)\.?\s*[A-Za-z]*)'
    match = re.search(address_pattern, text, re.IGNORECASE)
    if match:
        metadata['address'] = match.group(1).strip()
    
    # 6. PHONE NUMBERS - Multiple international formats
    phone_patterns = [
        r'(\+\d{1,3}\s*\d{2,3}\s*\d{3,4}\s*\d{3,4})',  # +27 82 434 4292, +44 20 7946 0958
        r'(\+\d{1,3}[\s\-]?\d{2,3}[\s\-]?\d{3}[\s\-]?\d{2,4}[\s\-]?\d{2,4})',  # +1-555-123-4567
        r'(\(\d{3}\)\s*\d{3}[\s\-]?\d{4})',  # (555) 123-4567
        r'(\d{3}[\s\-\.]\d{3}[\s\-\.]\d{4})',  # 555-123-4567, 555.123.4567
    ]
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        if phones:
            metadata['phone'] = phones[0].strip()
            if len(phones) > 1:
                metadata['phone_alt'] = phones[1].strip()
            break
    
    # 7. EMAIL
    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    match = re.search(email_pattern, text)
    if match:
        metadata['email'] = match.group(1).strip()
    
    # 8. DRAFT VERSION
    draft_patterns = [
        r'((?:first|second|third|fourth|fifth|final|revised?|shooting)\s+draft)',
        r'(draft\s*#?\s*\d+)',
        r'(v\.?\s*\d+)',
    ]
    for pattern in draft_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metadata['draft_version'] = match.group(1).strip()
            break
    
    # 9. DRAFT DATE
    date_patterns = [
        r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})',
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metadata['draft_date'] = match.group(1).strip()
            break
    
    # 10. COPYRIGHT
    copyright_pattern = r'(©|\(c\)|copyright)\s*(\d{4})?'
    match = re.search(copyright_pattern, text, re.IGNORECASE)
    if match:
        metadata['copyright'] = match.group(2) if match.group(2) else 'Yes'
    
    # 11. WGA REGISTRATION
    wga_pattern = r'(WGA\s*#?\s*\d+|WGAW?\s*Reg(?:istered)?\.?\s*#?\s*\d*)'
    match = re.search(wga_pattern, text, re.IGNORECASE)
    if match:
        metadata['wga_registration'] = match.group(1).strip()
    
    return metadata


def extract_writer_name(text):
    """Extract writer name from script text (legacy function)."""
    metadata = extract_title_page_metadata(text)
    return metadata.get('writers')


def detect_and_create_scenes_v2(script_id, pdf_path, full_text, pages_data):
    """
    Grammar-first scene detection with regex fallback.
    
    Uses the ScreenPy adapter to parse the PDF, then writes results
    to both `scenes` (for the existing UI) and `scene_candidates`
    (for tracking and A/B testing).
    
    Returns:
        (scene_count, parse_meta_dict)
    """
    from utils.scene_calculations import calculate_eighths_from_content, calculate_eighths_from_pages

    try:
        from services.screenplay_parser import parse_screenplay

        parsed_scenes, parse_meta = parse_screenplay(pdf_path, locale_codes=["en", "af"])
        parse_method = parse_meta.get("parse_method", "grammar")
        print(f"✓ ScreenPy adapter: {parse_method} found {len(parsed_scenes)} scenes")

    except Exception as e:
        print(f"⚠ Grammar adapter failed ({e}), falling back to legacy regex")
        return detect_and_create_scenes(script_id, full_text, pages_data), {"parse_method": "regex", "error": str(e)}

    if not parsed_scenes:
        print("⚠ Grammar returned 0 scenes, falling back to legacy regex")
        return detect_and_create_scenes(script_id, full_text, pages_data), {"parse_method": "regex", "reason": "0 scenes"}

    # Build page boundaries for eighths calculation
    page_boundaries = []
    current_pos = 0
    for page in pages_data:
        page_text = page['text']
        page_boundaries.append({
            'page': page['page_number'],
            'start': current_pos,
            'end': current_pos + len(page_text)
        })
        current_pos += len(page_text) + 2

    # Build all records first, then batch insert for performance
    scene_records = []
    candidate_records = []

    for idx, ps in enumerate(parsed_scenes):
        # Use scene text from parser (correct text source) with fallback
        scene_text = ps.scene_text or (full_text[ps.text_start:ps.text_end] if ps.text_start >= 0 else '')

        # Calculate scene length in eighths
        if scene_text and len(scene_text.strip()) > 50:
            page_length_eighths = calculate_eighths_from_content(scene_text)
        elif ps.page_start and ps.page_end:
            page_length_eighths = calculate_eighths_from_pages(ps.page_start, ps.page_end)
        else:
            page_length_eighths = 8

        # Parse location hierarchy into parent/specific
        loc_parent = ps.location_hierarchy[0] if ps.location_hierarchy else None
        loc_specific = ps.location_hierarchy[-1] if len(ps.location_hierarchy) > 1 else None

        scene_records.append({
            'script_id': script_id,
            'scene_number': ps.scene_number_original,
            'scene_order': ps.scene_order,
            'int_ext': ps.int_ext,
            'setting': ps.setting,
            'time_of_day': ps.time_of_day,
            'scene_text': scene_text[:5000],
            'text_start': ps.text_start,
            'text_end': ps.text_end,
            'page_start': ps.page_start,
            'page_end': ps.page_end,
            'page_length_eighths': page_length_eighths,
            'is_manual': False,
            'analysis_status': 'pending',
            # ScreenPy enrichments
            'location_parent': loc_parent,
            'location_specific': loc_specific,
            'location_hierarchy': ps.location_hierarchy,
            'shot_type': ps.shot_type,
            'speakers': list(ps.speakers.keys()) if ps.speakers else [],
            'transitions': ps.transitions or [],
            'parse_method': ps.parse_method or 'grammar',
        })

        candidate_records.append({
            'script_id': script_id,
            'scene_number_original': ps.scene_number_original,
            'scene_order': ps.scene_order,
            'int_ext': ps.int_ext,
            'setting': ps.setting,
            'time_of_day': ps.time_of_day,
            'page_start': ps.page_start,
            'page_end': ps.page_end,
            'text_start': ps.text_start,
            'text_end': ps.text_end,
            'content_hash': ps.content_hash,
            'status': 'detected',
            'location_hierarchy': ps.location_hierarchy,
            'speaker_list': ps.speakers,
            'shot_type': ps.shot_type,
            'transitions': ps.transitions,
            'parse_method': ps.parse_method,
        })

    # Batch insert scenes and candidates (chunks of 25 to avoid payload limits)
    BATCH_SIZE = 25
    scenes_created = 0
    candidates_created = 0

    for i in range(0, len(scene_records), BATCH_SIZE):
        batch = scene_records[i:i + BATCH_SIZE]
        try:
            supabase.table('scenes').insert(batch).execute()
            scenes_created += len(batch)
        except Exception as e:
            print(f"Error batch-inserting scenes {i}-{i+len(batch)}: {e}")
            # Fallback: insert one-by-one for this batch
            for rec in batch:
                try:
                    supabase.table('scenes').insert(rec).execute()
                    scenes_created += 1
                except Exception as inner_e:
                    print(f"Error creating scene {rec.get('scene_order')}: {inner_e}")

    for i in range(0, len(candidate_records), BATCH_SIZE):
        batch = candidate_records[i:i + BATCH_SIZE]
        try:
            supabase.table('scene_candidates').insert(batch).execute()
            candidates_created += len(batch)
        except Exception as e:
            print(f"Error batch-inserting candidates {i}-{i+len(batch)}: {e}")
            # Fallback: insert one-by-one for this batch
            for rec in batch:
                try:
                    supabase.table('scene_candidates').insert(rec).execute()
                    candidates_created += 1
                except Exception as inner_e:
                    print(f"Error creating candidate {rec.get('scene_order')}: {inner_e}")

    print(f"✓ Created {scenes_created} scenes + {candidates_created} candidates ({parse_method})")
    return scenes_created, parse_meta


def detect_and_create_scenes(script_id, full_text, pages_data=None):
    """
    Detect scenes using enhanced regex patterns.
    
    Handles:
    - Standard: INT. LOCATION - DAY
    - No space: INT.LOCATION - DAY
    - Multilingual: INT. LOCATION - DAG (Afrikaans), NUIT (French), NACHT (German)
    - Variations: CONTINUOUS, LATER, SAME TIME, MOMENTS LATER
    
    Args:
        script_id: The script UUID
        full_text: Complete script text
        pages_data: Optional list of {'page_number': int, 'text': str} for page calculation
    """
    import re
    
    # Build page boundaries for page_start/page_end calculation
    page_boundaries = []
    if pages_data:
        current_pos = 0
        for page in pages_data:
            page_text = page['text']
            page_boundaries.append({
                'page': page['page_number'],
                'start': current_pos,
                'end': current_pos + len(page_text)
            })
            current_pos += len(page_text) + 2  # +2 for '\n\n' separator
    
    def get_page_for_position(pos):
        """Find which page a text position falls on."""
        if not page_boundaries:
            return None
        for pb in page_boundaries:
            if pb['start'] <= pos < pb['end']:
                return pb['page']
        # If past all pages, return last page
        return page_boundaries[-1]['page'] if page_boundaries else None
    
    # Multilingual time of day patterns
    TIME_PATTERNS = r'(DAY|NIGHT|DAG|NAG|AAND|NACHT|TAG|JOUR|NUIT|DAWN|DUSK|MORNING|EVENING|AFTERNOON|CONTINUOUS|CONT\'?D?|LATER|SAME|MOMENTS?\s*LATER|SUNRISE|SUNSET)'
    TIME_WORDS = ['DAY', 'NIGHT', 'DAG', 'NAG', 'AAND', 'NACHT', 'TAG', 'JOUR', 'NUIT', 'DAWN', 'DUSK', 'MORNING', 'EVENING', 'AFTERNOON', 'CONTINUOUS', 'LATER', 'SAME', 'SUNRISE', 'SUNSET']
    
    # Scene header patterns (order matters - more specific first)
    patterns = [
        # Standard with dash: INT. LOCATION - DAY or INT.LOCATION - DAY
        rf'^(INT|EXT|INT/EXT|I/E)\.?\s*(.+?)\s*[-–—]\s*{TIME_PATTERNS}\s*$',
        
        # NO DASH - time at end: EXT. DRIVE IN NIGHT (non-standard but common)
        rf'^(INT|EXT|INT/EXT|I/E)\.?\s+(.+?)\s+{TIME_PATTERNS}\s*$',
        
        # Without time of day: INT. LOCATION
        r'^(INT|EXT|INT/EXT|I/E)\.?\s+([A-Z][A-Z0-9\s\'\-\.]+)$',
        
        # Full words: INTERIOR/EXTERIOR
        rf'^(INTERIOR|EXTERIOR)\s*[-–—:]\s*(.+?)(?:\s*[-–—]\s*{TIME_PATTERNS})?\s*$',
        
        # Numbered scenes: 1. INT. LOCATION - DAY
        rf'^\d+[A-Z]?\.\s*(INT|EXT|INT/EXT)\.?\s*(.+?)\s*[-–—]\s*{TIME_PATTERNS}\s*$',
    ]
    
    lines = full_text.split('\n')
    scenes = []
    current_pos = 0
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip empty or very short lines
        if len(line_stripped) < 5:
            continue
            
        for pattern in patterns:
            match = re.match(pattern, line_stripped, re.IGNORECASE)
            if match:
                # Extract INT/EXT
                int_ext = match.group(1).upper()
                if int_ext in ['INTERIOR', 'INT']:
                    int_ext = 'INT'
                elif int_ext in ['EXTERIOR', 'EXT']:
                    int_ext = 'EXT'
                elif int_ext in ['INT/EXT', 'I/E']:
                    int_ext = 'INT/EXT'
                
                # Extract setting (location)
                setting = match.group(2).strip() if match.group(2) else 'UNKNOWN'
                
                # Extract time of day (normalize multilingual)
                time_of_day = 'DAY'
                if match.lastindex >= 3 and match.group(3):
                    raw_time = match.group(3).upper().strip()
                    # Normalize multilingual time
                    if raw_time in ['DAG', 'TAG', 'JOUR', 'MORNING', 'AFTERNOON']:
                        time_of_day = 'DAY'
                    elif raw_time in ['NAG', 'AAND', 'NACHT', 'NUIT', 'EVENING']:
                        time_of_day = 'NIGHT'
                    elif raw_time in ['DAWN', 'SUNRISE']:
                        time_of_day = 'DAWN'
                    elif raw_time in ['DUSK', 'SUNSET']:
                        time_of_day = 'DUSK'
                    elif 'CONTINUOUS' in raw_time or 'CONT' in raw_time:
                        time_of_day = 'CONTINUOUS'
                    elif 'LATER' in raw_time:
                        time_of_day = 'LATER'
                    else:
                        time_of_day = raw_time
                
                # Calculate text position
                text_start = full_text.find(line_stripped, current_pos)
                
                scenes.append({
                    'int_ext': int_ext,
                    'setting': setting,
                    'time_of_day': time_of_day,
                    'text_start': text_start,
                    'line_number': i
                })
                current_pos = text_start + len(line_stripped) if text_start >= 0 else current_pos
                break
    
    # Build scene records for batch insert
    from utils.scene_calculations import calculate_eighths_from_content, calculate_eighths_from_pages
    scene_records = []
    
    for idx, scene in enumerate(scenes):
        # Calculate text_end (start of next scene or end of text)
        if idx + 1 < len(scenes):
            text_end = scenes[idx + 1]['text_start']
        else:
            text_end = len(full_text)
        
        scene_text = full_text[scene['text_start']:text_end] if scene['text_start'] >= 0 else ''
        
        # Calculate page numbers from text positions
        page_start = get_page_for_position(scene['text_start'])
        page_end = get_page_for_position(text_end - 1) if text_end > 0 else page_start
        
        # Calculate scene length in eighths
        if scene_text and len(scene_text.strip()) > 50:
            page_length_eighths = calculate_eighths_from_content(scene_text)
        elif page_start and page_end:
            page_length_eighths = calculate_eighths_from_pages(page_start, page_end)
        else:
            page_length_eighths = 8
        
        scene_records.append({
            'script_id': script_id,
            'scene_number': str(idx + 1),
            'scene_order': idx + 1,
            'int_ext': scene['int_ext'],
            'setting': scene['setting'],
            'time_of_day': scene['time_of_day'],
            'scene_text': scene_text[:5000],
            'text_start': scene['text_start'],
            'text_end': text_end,
            'page_start': page_start,
            'page_end': page_end,
            'page_length_eighths': page_length_eighths,
            'is_manual': False,
            'analysis_status': 'pending'
        })
    
    # Batch insert scenes (chunks of 25)
    BATCH_SIZE = 25
    scenes_created = 0
    for i in range(0, len(scene_records), BATCH_SIZE):
        batch = scene_records[i:i + BATCH_SIZE]
        try:
            supabase.table('scenes').insert(batch).execute()
            scenes_created += len(batch)
        except Exception as e:
            print(f"Error batch-inserting scenes {i}-{i+len(batch)}: {e}")
            for rec in batch:
                try:
                    supabase.table('scenes').insert(rec).execute()
                    scenes_created += 1
                except Exception as inner_e:
                    print(f"Error creating scene {rec.get('scene_order')}: {inner_e}")
    
    return scenes_created


# ============================================
# Scenes Endpoints
# ============================================

@supabase_bp.route('/api/scripts/<script_id>/scenes', methods=['GET'])
def get_scenes(script_id):
    """Get all scenes for a script."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('scenes').select('*').eq('script_id', script_id).order('scene_order').execute()
        
        scenes = []
        for scene in result.data:
            scenes.append({
                'id': scene['id'],
                'scene_id': scene['id'],  # Alias for compatibility
                'scene_number': scene['scene_number'],
                'int_ext': scene.get('int_ext', 'INT'),
                'setting': scene.get('setting', ''),
                'time_of_day': scene.get('time_of_day', 'DAY'),
                'description': scene.get('description', ''),
                'scene_text': scene.get('scene_text', ''),
                'characters': scene.get('characters', []),
                'props': scene.get('props', []),
                'wardrobe': scene.get('wardrobe', []),
                'special_fx': scene.get('special_fx', []),
                'vehicles': scene.get('vehicles', []),
                'locations': scene.get('locations', []),
                'sound': scene.get('sound', []),
                'makeup_hair': scene.get('makeup_hair', []),
                'atmosphere': scene.get('atmosphere', ''),
                'analysis_status': scene.get('analysis_status', 'pending'),
                'is_manual': scene.get('is_manual', False),
                'text_start': scene.get('text_start'),
                'text_end': scene.get('text_end'),
                'page_start': scene.get('page_start'),
                'page_end': scene.get('page_end'),
                # ScreenPy enrichments (Phase 1 + Phase 3)
                'location_parent': scene.get('location_parent'),
                'location_specific': scene.get('location_specific'),
                'location_hierarchy': scene.get('location_hierarchy', []),
                'shot_type': scene.get('shot_type'),
                'speakers': scene.get('speakers', []),
                'transitions': scene.get('transitions', []),
                'parse_method': scene.get('parse_method', 'regex'),
                # Story Days (Phase 2)
                'story_day': scene.get('story_day'),
                'story_day_label': scene.get('story_day_label'),
                'time_transition': scene.get('time_transition'),
                'is_new_story_day': scene.get('is_new_story_day', False),
                'story_day_confidence': scene.get('story_day_confidence'),
                'story_day_is_manual': scene.get('story_day_is_manual', False),
                'story_day_is_locked': scene.get('story_day_is_locked', False),
                'timeline_code': scene.get('timeline_code', 'PRESENT'),
            })
        
        return jsonify({'script_id': script_id, 'scenes': scenes}), 200
        
    except Exception as e:
        print(f"Error getting scenes: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scenes', methods=['POST'])
def create_scene():
    """Create a new scene (for manual labeling)."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        
        # Get next scene order
        script_id = data.get('script_id')
        result = supabase.table('scenes').select('scene_order').eq('script_id', script_id).order('scene_order', desc=True).limit(1).execute()
        
        next_order = 1
        if result.data:
            next_order = result.data[0]['scene_order'] + 1
        
        scene_data = {
            'script_id': script_id,
            'scene_number': data.get('scene_number', str(next_order)),
            'scene_order': next_order,
            'int_ext': data.get('int_ext', 'INT'),
            'setting': data.get('setting', 'Untitled Scene'),
            'time_of_day': data.get('time_of_day', 'DAY'),
            'scene_text': data.get('scene_text', ''),
            'text_start': data.get('text_start'),
            'text_end': data.get('text_end'),
            'is_manual': True,
            'analysis_status': 'pending'
        }
        
        result = supabase.table('scenes').insert(scene_data).execute()
        
        return jsonify(result.data[0]), 201
        
    except Exception as e:
        print(f"Error creating scene: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scenes/<scene_id>', methods=['PUT'])
def update_scene(scene_id):
    """Update a scene."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        
        # Only allow updating certain fields
        allowed_fields = ['scene_number', 'int_ext', 'setting', 'time_of_day', 
                          'description', 'characters', 'props', 'wardrobe', 
                          'special_fx', 'vehicles', 'analysis_status']
        
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        result = supabase.table('scenes').update(update_data).eq('id', scene_id).execute()
        
        return jsonify(result.data[0] if result.data else {}), 200
        
    except Exception as e:
        print(f"Error updating scene: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scenes/<scene_id>', methods=['DELETE'])
def delete_scene(scene_id):
    """Delete a scene."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get script_id before deleting for cascade recalculation
        scene_result = supabase.table('scenes').select('script_id').eq('id', scene_id).single().execute()
        script_id_for_recalc = scene_result.data.get('script_id') if scene_result.data else None
        
        supabase.table('scenes').delete().eq('id', scene_id).execute()
        
        # Cascade: recalculate story days
        if script_id_for_recalc:
            try:
                from services.story_day_service import recalculate_story_days
                recalculate_story_days(script_id_for_recalc)
            except Exception as recalc_err:
                print(f"Warning: Story day recalculation failed after delete: {recalc_err}")
        
        return jsonify({'message': 'Scene deleted successfully'}), 200
    except Exception as e:
        print(f"Error deleting scene: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# Scene Management Endpoints (Phase 1)
# ============================================

@supabase_bp.route('/api/scripts/<script_id>/scenes/manage', methods=['GET'])
@optional_auth
def get_scenes_for_management(script_id):
    """
    Get all scenes for scene management view.
    Includes omitted scenes and management-specific fields.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get script info - use * to handle missing columns gracefully
        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        
        script = script_result.data
        
        # Get all scenes - use * to handle missing columns gracefully
        result = supabase.table('scenes').select('*').eq('script_id', script_id).order('scene_order').execute()
        
        scenes = []
        for scene in result.data or []:
            scenes.append({
                'id': scene['id'],
                'scene_id': scene['id'],
                'scene_number': scene.get('scene_number'),
                'scene_number_original': scene.get('scene_number_original'),
                'scene_order': scene.get('scene_order'),
                'int_ext': scene.get('int_ext', 'INT'),
                'setting': scene.get('setting', ''),
                'time_of_day': scene.get('time_of_day', 'DAY'),
                'page_start': scene.get('page_start'),
                'page_end': scene.get('page_end'),
                'is_omitted': scene.get('is_omitted', False),
                'omitted_at': scene.get('omitted_at'),
                'locked_scene_number': scene.get('locked_scene_number'),
                'revision_number': scene.get('revision_number', 0),
                'analysis_status': scene.get('analysis_status', 'pending'),
                'character_count': len(scene.get('characters') or []),
                'prop_count': len(scene.get('props') or []),
                # Story Days (Phase 2)
                'story_day': scene.get('story_day'),
                'story_day_label': scene.get('story_day_label'),
                'time_transition': scene.get('time_transition'),
                'is_new_story_day': scene.get('is_new_story_day', False),
                'story_day_confidence': scene.get('story_day_confidence'),
                'story_day_is_manual': scene.get('story_day_is_manual', False),
                'story_day_is_locked': scene.get('story_day_is_locked', False),
                'timeline_code': scene.get('timeline_code', 'PRESENT'),
            })
        
        return jsonify({
            'script_id': script_id,
            'script': {
                'id': script['id'],
                'title': script['title'],
                'is_locked': script.get('is_locked', False),
                'locked_at': script.get('locked_at'),
                'current_revision_color': script.get('current_revision_color', 'white'),
                'total_story_days': script.get('total_story_days', 0)
            },
            'scenes': scenes,
            'total_scenes': len(scenes),
            'omitted_count': sum(1 for s in scenes if s.get('is_omitted'))
        }), 200
        
    except Exception as e:
        print(f"Error getting scenes for management: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/reorder', methods=['PATCH'])
@optional_auth
def reorder_scenes(script_id):
    """
    Reorder scenes by updating their scene_order based on array position.
    
    Request body:
    {
        "scene_ids": ["uuid1", "uuid2", "uuid3", ...]
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        scene_ids = data.get('scene_ids', [])
        
        if not scene_ids:
            return jsonify({'error': 'scene_ids array is required'}), 400
        
        # Check if script is locked
        script_result = supabase.table('scripts').select('is_locked').eq('id', script_id).single().execute()
        if script_result.data and script_result.data.get('is_locked'):
            return jsonify({'error': 'Cannot reorder scenes in a locked script'}), 403
        
        # Get current scene data for history
        current_scenes = supabase.table('scenes').select('id, scene_order').eq('script_id', script_id).execute()
        previous_order = {s['id']: s['scene_order'] for s in (current_scenes.data or [])}
        
        # Update scene_order for each scene
        for i, scene_id in enumerate(scene_ids, start=1):
            supabase.table('scenes').update({
                'scene_order': i
            }).eq('id', scene_id).eq('script_id', script_id).execute()
        
        # Record history for changed scenes
        user_id = get_user_id()
        for scene_id in scene_ids:
            old_order = previous_order.get(scene_id)
            new_order = scene_ids.index(scene_id) + 1
            if old_order != new_order:
                try:
                    supabase.table('scene_history').insert({
                        'scene_id': scene_id,
                        'change_type': 'reordered',
                        'previous_data': json.dumps({'scene_order': old_order}),
                        'changed_by': user_id
                    }).execute()
                except Exception as hist_err:
                    print(f"Warning: Failed to record history: {hist_err}")
        
        # Cascade: recalculate story days after reorder
        try:
            from services.story_day_service import recalculate_story_days
            recalculate_story_days(script_id)
        except Exception as recalc_err:
            print(f"Warning: Story day recalculation failed after reorder: {recalc_err}")
        
        return jsonify({
            'message': 'Scenes reordered successfully',
            'scene_count': len(scene_ids)
        }), 200
        
    except Exception as e:
        print(f"Error reordering scenes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/omit', methods=['PATCH'])
@optional_auth
def omit_scene(script_id, scene_id):
    """
    Mark a scene as omitted (or restore it).
    
    Request body:
    {
        "is_omitted": true/false
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        is_omitted = data.get('is_omitted', True)
        
        # Check if script is locked (gracefully handle missing column)
        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        if script_result.data and script_result.data.get('is_locked'):
            return jsonify({'error': 'Cannot modify scenes in a locked script'}), 403
        
        # Get current scene data for history
        current_scene = supabase.table('scenes').select('*').eq('id', scene_id).single().execute()
        
        if not current_scene.data:
            return jsonify({'error': 'Scene not found'}), 404
        
        # Update scene - try with new columns first, fall back to basic update
        from datetime import datetime
        
        try:
            # Try updating with new columns (after migration)
            update_data = {
                'is_omitted': is_omitted,
                'omitted_at': datetime.utcnow().isoformat() if is_omitted else None
            }
            result = supabase.table('scenes').update(update_data).eq('id', scene_id).execute()
        except Exception as col_err:
            # Columns don't exist yet - return error with migration hint
            print(f"Column error (migration needed): {col_err}")
            return jsonify({
                'error': 'Database migration required. Please run the migration in Supabase SQL Editor.',
                'migration_file': 'backend/db/migrations/003_script_editing_feature.sql'
            }), 500
        
        # Record history (skip if table doesn't exist)
        user_id = get_user_id()
        try:
            supabase.table('scene_history').insert({
                'scene_id': scene_id,
                'change_type': 'omitted' if is_omitted else 'restored',
                'previous_data': json.dumps({'is_omitted': current_scene.data.get('is_omitted', False)}),
                'changed_by': user_id
            }).execute()
        except Exception as hist_err:
            print(f"Warning: Failed to record history (table may not exist): {hist_err}")
        
        return jsonify({
            'message': f"Scene {'omitted' if is_omitted else 'restored'} successfully",
            'scene': result.data[0] if result.data else None
        }), 200
        
    except Exception as e:
        print(f"Error omitting scene: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/header', methods=['PATCH'])
@optional_auth
def update_scene_header(script_id, scene_id):
    """
    Update scene header (INT/EXT, setting, time of day).
    
    Request body:
    {
        "int_ext": "INT" | "EXT" | "INT/EXT",
        "setting": "LOCATION NAME",
        "time_of_day": "DAY" | "NIGHT" | "DAWN" | "DUSK" | "CONTINUOUS"
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        
        # Check if script is locked
        script_result = supabase.table('scripts').select('is_locked').eq('id', script_id).single().execute()
        if script_result.data and script_result.data.get('is_locked'):
            return jsonify({'error': 'Cannot modify scenes in a locked script'}), 403
        
        # Get current scene data for history
        current_scene = supabase.table('scenes').select('int_ext, setting, time_of_day').eq('id', scene_id).single().execute()
        
        if not current_scene.data:
            return jsonify({'error': 'Scene not found'}), 404
        
        # Only allow updating header fields
        allowed_fields = ['int_ext', 'setting', 'time_of_day']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        result = supabase.table('scenes').update(update_data).eq('id', scene_id).execute()
        
        # Record history
        user_id = get_user_id()
        try:
            supabase.table('scene_history').insert({
                'scene_id': scene_id,
                'change_type': 'modified',
                'previous_data': json.dumps(current_scene.data),
                'changed_by': user_id
            }).execute()
        except Exception as hist_err:
            print(f"Warning: Failed to record history: {hist_err}")
        
        return jsonify({
            'message': 'Scene header updated successfully',
            'scene': result.data[0] if result.data else None
        }), 200
        
    except Exception as e:
        print(f"Error updating scene header: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/history', methods=['GET'])
@optional_auth
def get_scene_history(script_id, scene_id):
    """Get change history for a scene."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('scene_history').select('*').eq(
            'scene_id', scene_id
        ).order('changed_at', desc=True).execute()
        
        return jsonify({
            'scene_id': scene_id,
            'history': result.data or []
        }), 200
        
    except Exception as e:
        print(f"Error getting scene history: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# Story Day Management Endpoints (Phase 2)
# ============================================

@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/toggle-new-day', methods=['PATCH'])
@optional_auth
def toggle_new_day(script_id, scene_id):
    """Toggle is_new_story_day on a scene, then recalculate."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        scene_result = supabase.table('scenes').select('is_new_story_day, scene_order').eq('id', scene_id).single().execute()
        if not scene_result.data:
            return jsonify({'error': 'Scene not found'}), 404

        current = scene_result.data.get('is_new_story_day', False)
        new_val = not current
        supabase.table('scenes').update({
            'is_new_story_day': new_val,
            'story_day_is_manual': True
        }).eq('id', scene_id).execute()

        from services.story_day_service import recalculate_story_days
        result = recalculate_story_days(script_id, start_from_order=scene_result.data.get('scene_order', 0))

        return jsonify({
            'message': f"Scene {'starts' if new_val else 'no longer starts'} a new day",
            'is_new_story_day': new_val,
            'recalculation': result
        }), 200
    except Exception as e:
        print(f"Error toggling new day: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/lock-story-day', methods=['PATCH'])
@optional_auth
def lock_story_day(script_id, scene_id):
    """Toggle story_day_is_locked on a scene."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        locked = data.get('locked')

        if locked is None:
            scene_result = supabase.table('scenes').select('story_day_is_locked').eq('id', scene_id).single().execute()
            if not scene_result.data:
                return jsonify({'error': 'Scene not found'}), 404
            locked = not scene_result.data.get('story_day_is_locked', False)

        supabase.table('scenes').update({
            'story_day_is_locked': locked
        }).eq('id', scene_id).execute()

        return jsonify({
            'message': f"Story day {'locked' if locked else 'unlocked'}",
            'story_day_is_locked': locked
        }), 200
    except Exception as e:
        print(f"Error locking story day: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/timeline-code', methods=['PATCH'])
@optional_auth
def set_timeline_code(script_id, scene_id):
    """Set timeline_code on a scene, then recalculate."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        code = data.get('timeline_code', 'PRESENT')
        valid_codes = ['PRESENT', 'FLASHBACK', 'DREAM', 'FANTASY', 'MONTAGE', 'TITLE_CARD']
        if code not in valid_codes:
            return jsonify({'error': f'Invalid timeline_code. Must be one of: {valid_codes}'}), 400

        scene_result = supabase.table('scenes').select('scene_order').eq('id', scene_id).single().execute()
        if not scene_result.data:
            return jsonify({'error': 'Scene not found'}), 404

        supabase.table('scenes').update({
            'timeline_code': code,
            'story_day_is_manual': True
        }).eq('id', scene_id).execute()

        from services.story_day_service import recalculate_story_days
        result = recalculate_story_days(script_id, start_from_order=scene_result.data.get('scene_order', 0))

        return jsonify({
            'message': f"Timeline code set to {code}",
            'timeline_code': code,
            'recalculation': result
        }), 200
    except Exception as e:
        print(f"Error setting timeline code: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/story-day', methods=['PATCH'])
@optional_auth
def set_story_day(script_id, scene_id):
    """Manually set story_day on a scene, lock it, then recalculate."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        story_day = data.get('story_day')
        if story_day is None or not isinstance(story_day, int) or story_day < 1:
            return jsonify({'error': 'story_day must be a positive integer'}), 400

        scene_result = supabase.table('scenes').select('scene_order').eq('id', scene_id).single().execute()
        if not scene_result.data:
            return jsonify({'error': 'Scene not found'}), 404

        supabase.table('scenes').update({
            'story_day': story_day,
            'story_day_is_manual': True,
            'story_day_is_locked': True
        }).eq('id', scene_id).execute()

        from services.story_day_service import recalculate_story_days
        result = recalculate_story_days(script_id, start_from_order=scene_result.data.get('scene_order', 0))

        return jsonify({
            'message': f"Story day set to {story_day} and locked",
            'story_day': story_day,
            'recalculation': result
        }), 200
    except Exception as e:
        print(f"Error setting story day: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/story-days/calculate', methods=['POST'])
@optional_auth
def calculate_story_days(script_id):
    """Trigger full recalculation of story days for a script."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        from services.story_day_service import recalculate_story_days
        result = recalculate_story_days(script_id, start_from_order=0)
        return jsonify({
            'message': 'Story days recalculated',
            **result
        }), 200
    except Exception as e:
        print(f"Error calculating story days: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/story-days/summary', methods=['GET'])
@optional_auth
def story_day_summary(script_id):
    """Get story day summary for a script."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        from services.story_day_service import get_story_day_summary
        summary = get_story_day_summary(script_id)
        return jsonify(summary), 200
    except Exception as e:
        print(f"Error getting story day summary: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/story-days/bulk-update', methods=['POST'])
@optional_auth
def bulk_update_story_days(script_id):
    """
    Bulk update story day fields on multiple scenes.
    
    Request body:
    {
        "updates": [
            {"scene_id": "uuid", "story_day": 2, "is_new_story_day": true, "timeline_code": "PRESENT"},
            ...
        ]
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        updates = data.get('updates', [])
        if not updates:
            return jsonify({'error': 'updates array is required'}), 400

        valid_codes = ['PRESENT', 'FLASHBACK', 'DREAM', 'FANTASY', 'MONTAGE', 'TITLE_CARD']

        for update in updates:
            scene_id = update.get('scene_id')
            if not scene_id:
                continue
            patch = {'story_day_is_manual': True}
            if 'story_day' in update:
                patch['story_day'] = update['story_day']
                patch['story_day_is_locked'] = True
            if 'is_new_story_day' in update:
                patch['is_new_story_day'] = update['is_new_story_day']
            if 'timeline_code' in update and update['timeline_code'] in valid_codes:
                patch['timeline_code'] = update['timeline_code']
            supabase.table('scenes').update(patch).eq('id', scene_id).eq('script_id', script_id).execute()

        from services.story_day_service import recalculate_story_days
        result = recalculate_story_days(script_id, start_from_order=0)

        return jsonify({
            'message': f"Updated {len(updates)} scenes",
            'scenes_updated': len(updates),
            'recalculation': result
        }), 200
    except Exception as e:
        print(f"Error bulk updating story days: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# Scene Operations (Phase 2)
# ============================================

@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/split', methods=['POST'])
@optional_auth
def split_scene(script_id, scene_id):
    """
    Split a scene into two scenes.
    
    Request body:
    {
        "split_at_line": 10,           // Line number to split at (optional)
        "new_scene_suffix": "A",       // Suffix for new scenes (e.g., "15" becomes "15A", "15B")
        "first_scene_text": "...",     // Text for first half (optional)
        "second_scene_text": "..."     // Text for second half (optional)
    }
    
    Industry standard: When splitting scene 15, it becomes 15A and 15B.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        
        # Check if script is locked
        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        if script_result.data and script_result.data.get('is_locked'):
            return jsonify({'error': 'Cannot split scenes in a locked script'}), 403
        
        # Get the scene to split
        scene_result = supabase.table('scenes').select('*').eq('id', scene_id).single().execute()
        if not scene_result.data:
            return jsonify({'error': 'Scene not found'}), 404
        
        original_scene = scene_result.data
        original_number = original_scene.get('scene_number', '1')
        original_order = original_scene.get('scene_order', 1)
        
        # Determine new scene numbers
        # If scene is "15", split creates "15A" and "15B"
        # If scene is already "15A", split creates "15A1" and "15A2"
        base_number = original_number.rstrip('ABCDEFGHIJ0123456789')
        if base_number == original_number:
            # Simple number like "15"
            first_number = f"{original_number}A"
            second_number = f"{original_number}B"
        else:
            # Already has suffix like "15A"
            first_number = f"{original_number}1"
            second_number = f"{original_number}2"
        
        # Update original scene to become first part
        first_scene_data = {
            'scene_number': first_number,
            'scene_text': data.get('first_scene_text', original_scene.get('scene_text', '')),
        }
        supabase.table('scenes').update(first_scene_data).eq('id', scene_id).execute()
        
        # Shift all subsequent scenes' order by 1
        subsequent_scenes = supabase.table('scenes').select('id, scene_order').eq(
            'script_id', script_id
        ).gt('scene_order', original_order).execute()
        
        for scene in (subsequent_scenes.data or []):
            supabase.table('scenes').update({
                'scene_order': scene['scene_order'] + 1
            }).eq('id', scene['id']).execute()
        
        # Create second scene
        second_scene_data = {
            'script_id': script_id,
            'scene_number': second_number,
            'scene_order': original_order + 1,
            'int_ext': original_scene.get('int_ext', 'INT'),
            'setting': original_scene.get('setting', ''),
            'time_of_day': original_scene.get('time_of_day', 'DAY'),
            'scene_text': data.get('second_scene_text', ''),
            'parent_scene_id': scene_id,  # Track that this came from a split
            'analysis_status': 'pending',
            'page_start': original_scene.get('page_start'),
            'page_end': original_scene.get('page_end'),
        }
        
        new_scene_result = supabase.table('scenes').insert(second_scene_data).execute()
        new_scene = new_scene_result.data[0] if new_scene_result.data else None
        
        # Record history
        user_id = get_user_id()
        try:
            supabase.table('scene_history').insert({
                'scene_id': scene_id,
                'change_type': 'split',
                'previous_data': json.dumps({
                    'scene_number': original_number,
                    'scene_order': original_order
                }),
                'changed_by': user_id
            }).execute()
        except Exception as hist_err:
            print(f"Warning: Failed to record history: {hist_err}")
        
        # Cascade: recalculate story days after split
        try:
            from services.story_day_service import recalculate_story_days
            recalculate_story_days(script_id)
        except Exception as recalc_err:
            print(f"Warning: Story day recalculation failed after split: {recalc_err}")
        
        return jsonify({
            'message': f"Scene {original_number} split into {first_number} and {second_number}",
            'first_scene': {
                'id': scene_id,
                'scene_number': first_number
            },
            'second_scene': new_scene
        }), 200
        
    except Exception as e:
        print(f"Error splitting scene: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/merge', methods=['POST'])
@optional_auth
def merge_scenes(script_id, scene_id):
    """
    Merge two adjacent scenes into one.
    
    Request body:
    {
        "merge_with_scene_id": "uuid",  // Scene to merge with (must be adjacent)
        "keep_scene_number": "first"    // "first" or "second" - which number to keep
    }
    
    Industry standard: Merged scene keeps one number, the other becomes OMITTED.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        merge_with_id = data.get('merge_with_scene_id')
        keep_number = data.get('keep_scene_number', 'first')
        
        if not merge_with_id:
            return jsonify({'error': 'merge_with_scene_id is required'}), 400
        
        # Check if script is locked
        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        if script_result.data and script_result.data.get('is_locked'):
            return jsonify({'error': 'Cannot merge scenes in a locked script'}), 403
        
        # Get both scenes
        first_scene = supabase.table('scenes').select('*').eq('id', scene_id).single().execute()
        second_scene = supabase.table('scenes').select('*').eq('id', merge_with_id).single().execute()
        
        if not first_scene.data or not second_scene.data:
            return jsonify({'error': 'One or both scenes not found'}), 404
        
        scene_a = first_scene.data
        scene_b = second_scene.data
        
        # Ensure scenes are adjacent
        order_diff = abs(scene_a.get('scene_order', 0) - scene_b.get('scene_order', 0))
        if order_diff != 1:
            return jsonify({'error': 'Scenes must be adjacent to merge'}), 400
        
        # Determine which scene is first (by order)
        if scene_a.get('scene_order', 0) < scene_b.get('scene_order', 0):
            primary_scene = scene_a
            secondary_scene = scene_b
            primary_id = scene_id
            secondary_id = merge_with_id
        else:
            primary_scene = scene_b
            secondary_scene = scene_a
            primary_id = merge_with_id
            secondary_id = scene_id
        
        # Merge text content
        merged_text = (primary_scene.get('scene_text', '') or '') + '\n\n' + (secondary_scene.get('scene_text', '') or '')
        
        # Merge characters and props
        merged_characters = list(set(
            (primary_scene.get('characters') or []) + 
            (secondary_scene.get('characters') or [])
        ))
        merged_props = list(set(
            (primary_scene.get('props') or []) + 
            (secondary_scene.get('props') or [])
        ))
        
        # Determine which scene number to keep
        if keep_number == 'second':
            kept_number = secondary_scene.get('scene_number')
        else:
            kept_number = primary_scene.get('scene_number')
        
        # Update primary scene with merged content
        supabase.table('scenes').update({
            'scene_number': kept_number,
            'scene_text': merged_text.strip(),
            'characters': merged_characters,
            'props': merged_props,
            'page_end': secondary_scene.get('page_end') or primary_scene.get('page_end'),
            'analysis_status': 'pending'  # Re-analyze after merge
        }).eq('id', primary_id).execute()
        
        # Mark secondary scene as merged (omitted with reference)
        from datetime import datetime
        supabase.table('scenes').update({
            'is_omitted': True,
            'omitted_at': datetime.utcnow().isoformat(),
            'merged_into_scene_id': primary_id
        }).eq('id', secondary_id).execute()
        
        # Record history
        user_id = get_user_id()
        try:
            supabase.table('scene_history').insert({
                'scene_id': primary_id,
                'change_type': 'merged',
                'previous_data': json.dumps({
                    'merged_scene_id': secondary_id,
                    'merged_scene_number': secondary_scene.get('scene_number')
                }),
                'changed_by': user_id
            }).execute()
        except Exception as hist_err:
            print(f"Warning: Failed to record history: {hist_err}")
        
        # Cascade: recalculate story days after merge
        try:
            from services.story_day_service import recalculate_story_days
            recalculate_story_days(script_id)
        except Exception as recalc_err:
            print(f"Warning: Story day recalculation failed after merge: {recalc_err}")
        
        return jsonify({
            'message': f"Scenes merged successfully",
            'merged_scene': {
                'id': primary_id,
                'scene_number': kept_number
            },
            'omitted_scene': {
                'id': secondary_id,
                'scene_number': secondary_scene.get('scene_number')
            }
        }), 200
        
    except Exception as e:
        print(f"Error merging scenes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/manual', methods=['POST'])
@optional_auth
def add_manual_scene(script_id):
    """
    Add a new scene manually.
    
    Request body:
    {
        "scene_number": "15A",          // Optional, auto-generated if not provided
        "int_ext": "INT",
        "setting": "OFFICE",
        "time_of_day": "DAY",
        "insert_after_scene_id": "uuid", // Optional, insert after this scene
        "scene_text": "..."             // Optional
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        
        # Check if script is locked
        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        if script_result.data and script_result.data.get('is_locked'):
            return jsonify({'error': 'Cannot add scenes to a locked script'}), 403
        
        # Determine scene order
        insert_after_id = data.get('insert_after_scene_id')
        
        if insert_after_id:
            # Insert after specific scene
            after_scene = supabase.table('scenes').select('scene_order').eq('id', insert_after_id).single().execute()
            if not after_scene.data:
                return jsonify({'error': 'Insert after scene not found'}), 404
            
            new_order = after_scene.data['scene_order'] + 1
            
            # Shift subsequent scenes
            subsequent = supabase.table('scenes').select('id, scene_order').eq(
                'script_id', script_id
            ).gte('scene_order', new_order).execute()
            
            for scene in (subsequent.data or []):
                supabase.table('scenes').update({
                    'scene_order': scene['scene_order'] + 1
                }).eq('id', scene['id']).execute()
        else:
            # Add at end
            max_order = supabase.table('scenes').select('scene_order').eq(
                'script_id', script_id
            ).order('scene_order', desc=True).limit(1).execute()
            
            new_order = (max_order.data[0]['scene_order'] + 1) if max_order.data else 1
        
        # Generate scene number if not provided
        scene_number = data.get('scene_number')
        if not scene_number:
            scene_number = str(new_order)
        
        # Create the new scene
        new_scene_data = {
            'script_id': script_id,
            'scene_number': scene_number,
            'scene_order': new_order,
            'int_ext': data.get('int_ext', 'INT'),
            'setting': data.get('setting', 'NEW LOCATION'),
            'time_of_day': data.get('time_of_day', 'DAY'),
            'scene_text': data.get('scene_text', ''),
            'is_manual': True,
            'analysis_status': 'pending'
        }
        
        result = supabase.table('scenes').insert(new_scene_data).execute()
        new_scene = result.data[0] if result.data else None
        
        # Record history
        user_id = get_user_id()
        if new_scene:
            try:
                supabase.table('scene_history').insert({
                    'scene_id': new_scene['id'],
                    'change_type': 'created',
                    'previous_data': None,
                    'changed_by': user_id
                }).execute()
            except Exception as hist_err:
                print(f"Warning: Failed to record history: {hist_err}")
        
        # Cascade: recalculate story days after adding scene
        try:
            from services.story_day_service import recalculate_story_days
            recalculate_story_days(script_id)
        except Exception as recalc_err:
            print(f"Warning: Story day recalculation failed after add: {recalc_err}")
        
        return jsonify({
            'message': 'Scene created successfully',
            'scene': new_scene
        }), 201
        
    except Exception as e:
        print(f"Error adding manual scene: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/merge-multiple', methods=['POST'])
@optional_auth
def merge_multiple_scenes(script_id):
    """
    Merge multiple scenes into one.
    
    Request body:
    {
        "scene_ids": ["uuid1", "uuid2", "uuid3"],  // Scenes to merge (must be contiguous)
        "keep_scene_id": "uuid1"                    // Which scene's number to keep
    }
    
    Industry standard: One scene number is kept, all others become OMITTED.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        scene_ids = data.get('scene_ids', [])
        keep_scene_id = data.get('keep_scene_id')
        
        if len(scene_ids) < 2:
            return jsonify({'error': 'At least 2 scenes required for merge'}), 400
        
        if not keep_scene_id or keep_scene_id not in scene_ids:
            return jsonify({'error': 'keep_scene_id must be one of the scene_ids'}), 400
        
        # Check if script is locked
        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        if script_result.data and script_result.data.get('is_locked'):
            return jsonify({'error': 'Cannot merge scenes in a locked script'}), 403
        
        # Get all scenes to merge
        scenes_result = supabase.table('scenes').select('*').in_('id', scene_ids).execute()
        scenes = scenes_result.data or []
        
        if len(scenes) != len(scene_ids):
            return jsonify({'error': 'One or more scenes not found'}), 404
        
        # Sort by scene_order
        scenes.sort(key=lambda s: s.get('scene_order', 0))
        
        # Validate contiguity - check for gaps
        for i in range(len(scenes) - 1):
            current_order = scenes[i].get('scene_order', 0)
            next_order = scenes[i + 1].get('scene_order', 0)
            
            # Check if there are active scenes between them that aren't in our list
            between_result = supabase.table('scenes').select('id').eq(
                'script_id', script_id
            ).gt('scene_order', current_order).lt('scene_order', next_order).eq(
                'is_omitted', False
            ).execute()
            
            if between_result.data:
                return jsonify({'error': 'Selected scenes must be adjacent (no active scenes between them)'}), 400
        
        # Find the scene to keep
        keep_scene = next((s for s in scenes if s['id'] == keep_scene_id), None)
        omit_scenes = [s for s in scenes if s['id'] != keep_scene_id]
        
        # Merge all text content
        merged_text = '\n\n'.join([
            s.get('scene_text', '') or '' for s in scenes
        ]).strip()
        
        # Merge characters and props from all scenes
        all_characters = []
        all_props = []
        for s in scenes:
            all_characters.extend(s.get('characters') or [])
            all_props.extend(s.get('props') or [])
        
        merged_characters = list(set(all_characters))
        merged_props = list(set(all_props))
        
        # Get page range
        page_start = min(s.get('page_start') or 999 for s in scenes)
        page_end = max(s.get('page_end') or 0 for s in scenes)
        
        # Update the kept scene with merged content
        supabase.table('scenes').update({
            'scene_text': merged_text,
            'characters': merged_characters,
            'props': merged_props,
            'page_start': page_start if page_start != 999 else None,
            'page_end': page_end if page_end != 0 else None,
            'analysis_status': 'pending'  # Re-analyze after merge
        }).eq('id', keep_scene_id).execute()
        
        # Mark all other scenes as omitted
        from datetime import datetime
        for scene in omit_scenes:
            supabase.table('scenes').update({
                'is_omitted': True,
                'omitted_at': datetime.utcnow().isoformat(),
                'merged_into_scene_id': keep_scene_id
            }).eq('id', scene['id']).execute()
        
        # Record history
        user_id = get_user_id()
        try:
            supabase.table('scene_history').insert({
                'scene_id': keep_scene_id,
                'change_type': 'multi_merged',
                'previous_data': json.dumps({
                    'merged_scene_ids': [s['id'] for s in omit_scenes],
                    'merged_scene_numbers': [s.get('scene_number') for s in omit_scenes]
                }),
                'changed_by': user_id
            }).execute()
        except Exception as hist_err:
            print(f"Warning: Failed to record history: {hist_err}")
        
        # Cascade: recalculate story days after multi-merge
        try:
            from services.story_day_service import recalculate_story_days
            recalculate_story_days(script_id)
        except Exception as recalc_err:
            print(f"Warning: Story day recalculation failed after multi-merge: {recalc_err}")
        
        return jsonify({
            'message': f"{len(scene_ids)} scenes merged successfully",
            'kept_scene': {
                'id': keep_scene_id,
                'scene_number': keep_scene.get('scene_number')
            },
            'omitted_scenes': [
                {'id': s['id'], 'scene_number': s.get('scene_number')} 
                for s in omit_scenes
            ]
        }), 200
        
    except Exception as e:
        print(f"Error merging multiple scenes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# Script Lock & Export (Phase 4)
# ============================================

@supabase_bp.route('/api/scripts/<script_id>/lock', methods=['POST'])
@optional_auth
def lock_script(script_id):
    """
    Lock a script for production (shooting script).
    
    When locked:
    - Scene numbers become permanent (locked_scene_number)
    - No more scene reordering, splitting, merging, or adding
    - Script is ready for shooting script export
    
    Request body:
    {
        "revision_color": "WHITE"  // Optional, default is WHITE for first lock
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json() or {}
        revision_color = data.get('revision_color', 'WHITE')
        
        # Valid revision colors (industry standard order)
        valid_colors = ['WHITE', 'BLUE', 'PINK', 'YELLOW', 'GREEN', 'GOLDENROD', 'BUFF', 'SALMON', 'CHERRY', 'TAN']
        if revision_color not in valid_colors:
            return jsonify({'error': f'Invalid revision color. Must be one of: {", ".join(valid_colors)}'}), 400
        
        # Check if script exists
        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        if not script_result.data:
            return jsonify({'error': 'Script not found'}), 404
        
        script = script_result.data
        
        if script.get('is_locked'):
            return jsonify({'error': 'Script is already locked'}), 400
        
        # Get all active scenes
        scenes_result = supabase.table('scenes').select('*').eq('script_id', script_id).eq('is_omitted', False).order('scene_order').execute()
        scenes = scenes_result.data or []
        
        # Lock each scene's number
        for scene in scenes:
            supabase.table('scenes').update({
                'locked_scene_number': scene.get('scene_number'),
                'revision_number': 1
            }).eq('id', scene['id']).execute()
        
        # Lock the script
        from datetime import datetime
        user_id = get_user_id()
        
        supabase.table('scripts').update({
            'is_locked': True,
            'locked_at': datetime.utcnow().isoformat(),
            'locked_by': user_id,
            'current_revision_color': revision_color
        }).eq('id', script_id).execute()
        
        # Create initial version record
        try:
            supabase.table('script_versions').insert({
                'script_id': script_id,
                'version_number': 1,
                'revision_color': revision_color,
                'created_by': user_id,
                'notes': 'Initial locked version (shooting script)'
            }).execute()
        except Exception as ver_err:
            print(f"Warning: Failed to create version record: {ver_err}")
        
        return jsonify({
            'message': 'Script locked successfully',
            'script_id': script_id,
            'revision_color': revision_color,
            'locked_scenes': len(scenes)
        }), 200
        
    except Exception as e:
        print(f"Error locking script: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/unlock', methods=['POST'])
@optional_auth
def unlock_script(script_id):
    """
    Unlock a script (revert to working draft).
    
    WARNING: This removes the shooting script lock.
    Scene numbers remain but are no longer locked.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Check if script exists and is locked
        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        if not script_result.data:
            return jsonify({'error': 'Script not found'}), 404
        
        if not script_result.data.get('is_locked'):
            return jsonify({'error': 'Script is not locked'}), 400
        
        # Unlock the script
        supabase.table('scripts').update({
            'is_locked': False,
            'locked_at': None,
            'locked_by': None
        }).eq('id', script_id).execute()
        
        return jsonify({
            'message': 'Script unlocked successfully',
            'script_id': script_id
        }), 200
        
    except Exception as e:
        print(f"Error unlocking script: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/shooting-script', methods=['GET'])
@optional_auth
def get_shooting_script_data(script_id):
    """
    Get shooting script data for preview/export.
    
    Returns all scenes with their locked numbers, formatted for shooting script.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get script
        script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
        if not script_result.data:
            return jsonify({'error': 'Script not found'}), 404
        
        script = script_result.data
        
        # Get all scenes (including omitted for continuity)
        scenes_result = supabase.table('scenes').select('*').eq('script_id', script_id).order('scene_order').execute()
        scenes = scenes_result.data or []
        
        # Format for shooting script
        shooting_scenes = []
        for scene in scenes:
            scene_number = scene.get('locked_scene_number') or scene.get('scene_number')
            
            shooting_scenes.append({
                'id': scene['id'],
                'scene_number': scene_number,
                'is_omitted': scene.get('is_omitted', False),
                'int_ext': scene.get('int_ext', 'INT'),
                'setting': scene.get('setting', ''),
                'time_of_day': scene.get('time_of_day', 'DAY'),
                'page_start': scene.get('page_start'),
                'page_end': scene.get('page_end'),
                'characters': scene.get('characters', []),
                'scene_text': scene.get('scene_text', ''),
                'revision_number': scene.get('revision_number', 1)
            })
        
        return jsonify({
            'script': {
                'id': script['id'],
                'title': script.get('title', 'Untitled'),
                'writer_name': script.get('writer_name'),
                'is_locked': script.get('is_locked', False),
                'locked_at': script.get('locked_at'),
                'revision_color': script.get('current_revision_color', 'WHITE')
            },
            'scenes': shooting_scenes,
            'total_scenes': len([s for s in shooting_scenes if not s['is_omitted']]),
            'omitted_scenes': len([s for s in shooting_scenes if s['is_omitted']])
        }), 200
        
    except Exception as e:
        print(f"Error getting shooting script data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# Stats Endpoint
# ============================================

@supabase_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Total scripts
        scripts_result = supabase.table('scripts').select('id', count='exact').execute()
        total_scripts = scripts_result.count or 0
        
        # Total scenes
        scenes_result = supabase.table('scenes').select('id', count='exact').execute()
        total_scenes = scenes_result.count or 0
        
        # Recent scripts
        recent_result = supabase.table('scripts').select('id, title, created_at, writer_name').order('created_at', desc=True).limit(3).execute()
        
        recent_scripts = []
        for script in recent_result.data:
            scene_count_result = supabase.table('scenes').select('id', count='exact').eq('script_id', script['id']).execute()
            recent_scripts.append({
                'script_id': script['id'],
                'script_name': script['title'],
                'upload_date': script['created_at'],
                'writer_name': script.get('writer_name'),
                'scene_count': scene_count_result.count or 0
            })
        
        return jsonify({
            'total_scripts': total_scripts,
            'total_scenes': total_scenes,
            'analyzed_scripts': total_scripts,  # Simplified for now
            'pending_scripts': 0,
            'recent_scripts': recent_scripts
        }), 200
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# Full Text Endpoint (for Scene Editor)
# ============================================

@supabase_bp.route('/api/scripts/<script_id>/full-text', methods=['GET'])
def get_script_full_text(script_id):
    """Get full script text for manual scene labeling."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('scripts').select('full_text, title').eq('id', script_id).single().execute()
        
        return jsonify({
            'script_id': script_id,
            'title': result.data.get('title'),
            'full_text': result.data.get('full_text', '')
        }), 200
        
    except Exception as e:
        print(f"Error getting full text: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/page-mapping', methods=['GET'])
def get_page_mapping(script_id):
    """
    Calculate page numbers for each scene based on text positions.
    
    Returns a mapping of scene_id -> {page_start, page_end}
    This is used for bidirectional sync between PDF viewer and scene list.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get all pages with cumulative text lengths
        pages_result = supabase.table('script_pages').select('page_number, page_text').eq('script_id', script_id).order('page_number').execute()
        
        if not pages_result.data:
            return jsonify({'error': 'No pages found for script'}), 404
        
        # Build cumulative text position map
        # page_boundaries[i] = (start_pos, end_pos) for page i+1
        page_boundaries = []
        cumulative_pos = 0
        for page in pages_result.data:
            page_text = page.get('page_text', '')
            start_pos = cumulative_pos
            end_pos = cumulative_pos + len(page_text)
            page_boundaries.append({
                'page': page['page_number'],
                'start': start_pos,
                'end': end_pos
            })
            cumulative_pos = end_pos
        
        # Get all scenes with text positions
        scenes_result = supabase.table('scenes').select('id, scene_number, text_start, text_end').eq('script_id', script_id).order('scene_order').execute()
        
        if not scenes_result.data:
            return jsonify({'error': 'No scenes found for script'}), 404
        
        # Map each scene to its page range
        scene_pages = {}
        for scene in scenes_result.data:
            text_start = scene.get('text_start', 0) or 0
            text_end = scene.get('text_end', 0) or 0
            
            page_start = 1
            page_end = 1
            
            # Find which page contains text_start
            for pb in page_boundaries:
                if pb['start'] <= text_start < pb['end']:
                    page_start = pb['page']
                    break
            
            # Find which page contains text_end
            for pb in page_boundaries:
                if pb['start'] < text_end <= pb['end']:
                    page_end = pb['page']
                    break
            
            scene_pages[scene['id']] = {
                'scene_number': scene['scene_number'],
                'page_start': page_start,
                'page_end': page_end
            }
        
        # Also create reverse mapping: page -> [scene_ids]
        page_to_scenes = {}
        for scene_id, data in scene_pages.items():
            for page in range(data['page_start'], data['page_end'] + 1):
                if page not in page_to_scenes:
                    page_to_scenes[page] = []
                page_to_scenes[page].append({
                    'scene_id': scene_id,
                    'scene_number': data['scene_number']
                })
        
        return jsonify({
            'script_id': script_id,
            'total_pages': len(page_boundaries),
            'scene_pages': scene_pages,
            'page_to_scenes': page_to_scenes
        }), 200
        
    except Exception as e:
        print(f"Error calculating page mapping: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/pdf-url', methods=['GET'])
def get_pdf_url(script_id):
    """
    Get a signed URL for the script's PDF file.
    
    The URL is valid for 1 hour (3600 seconds).
    This allows the frontend to display the PDF in a viewer.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get the file path from the script record
        result = supabase.table('scripts').select('file_path, file_name, title').eq('id', script_id).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Script not found'}), 404
        
        file_path = result.data.get('file_path')
        if not file_path:
            return jsonify({'error': 'No PDF file associated with this script'}), 404
        
        # Generate a signed URL valid for 1 hour
        signed_url_response = supabase.storage.from_('scripts').create_signed_url(
            file_path,
            3600  # 1 hour expiry
        )
        
        if not signed_url_response or 'signedURL' not in signed_url_response:
            return jsonify({'error': 'Failed to generate signed URL'}), 500
        
        return jsonify({
            'script_id': script_id,
            'pdf_url': signed_url_response['signedURL'],
            'file_name': result.data.get('file_name'),
            'title': result.data.get('title'),
            'expires_in': 3600
        }), 200
        
    except Exception as e:
        print(f"Error getting PDF URL: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# Scene Analysis Endpoints
# ============================================

@supabase_bp.route('/api/scenes/<scene_id>/analyze', methods=['POST'])
def analyze_scene(scene_id):
    """
    Analyze a single scene using Gemini AI.
    
    Extracts: characters, props, wardrobe, special_fx, vehicles, description
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get scene data
        scene_result = supabase.table('scenes').select('*').eq('id', scene_id).single().execute()
        scene = scene_result.data
        
        if not scene:
            return jsonify({'error': 'Scene not found'}), 404
        
        # Update status to analyzing
        supabase.table('scenes').update({'analysis_status': 'analyzing'}).eq('id', scene_id).execute()
        
        # Get scene text
        scene_text = scene.get('scene_text', '')
        if not scene_text or len(scene_text) < 10:
            # If no scene text, try to get from full script
            script_result = supabase.table('scripts').select('full_text').eq('id', scene['script_id']).single().execute()
            full_text = script_result.data.get('full_text', '')
            
            text_start = scene.get('text_start', 0)
            text_end = scene.get('text_end', len(full_text))
            scene_text = full_text[text_start:text_end] if full_text else ''
        
        if not scene_text:
            supabase.table('scenes').update({'analysis_status': 'error'}).eq('id', scene_id).execute()
            return jsonify({'error': 'No scene text available'}), 400
        
        # Phase 2: Extract pre-parsed data for prompt optimization
        known_speakers = scene.get('speakers') or {}
        if isinstance(known_speakers, str):
            known_speakers = json.loads(known_speakers)
        # Normalize: speakers may be a list of names (from detect_and_create_scenes_v2)
        if isinstance(known_speakers, list):
            known_speakers = {name: {} for name in known_speakers}
        scene_shot_type = scene.get('shot_type')
        scene_location_hierarchy = scene.get('location_hierarchy') or []
        if isinstance(scene_location_hierarchy, str):
            scene_location_hierarchy = json.loads(scene_location_hierarchy)
        
        has_speakers = known_speakers and len(known_speakers) > 0
        
        # Story Days Phase 1: Fetch previous scene for context injection
        prev_scene_context = None
        current_order = scene.get('scene_order') or scene.get('scene_number', 0)
        if current_order and current_order > 1:
            from db.supabase_client import db as supa_db
            prev_scene = supa_db.get_scene_by_order(scene['script_id'], current_order - 1)
            if prev_scene:
                prev_scene_context = prev_scene
        
        # Call Gemini for analysis with pre-extracted context
        analysis = analyze_scene_with_gemini(
            scene_text, scene.get('setting', ''),
            known_speakers=known_speakers if has_speakers else None,
            shot_type=scene_shot_type,
            location_hierarchy=scene_location_hierarchy,
            prev_scene_context=prev_scene_context,
        )
        
        # Recalculate scene length in eighths with full scene text
        from utils.scene_calculations import calculate_eighths_from_content, calculate_eighths_from_pages
        if scene_text and len(scene_text.strip()) > 50:
            page_length_eighths = calculate_eighths_from_content(scene_text)
        elif scene.get('page_start') and scene.get('page_end'):
            page_length_eighths = calculate_eighths_from_pages(scene.get('page_start'), scene.get('page_end'))
        else:
            page_length_eighths = 8  # Default to 1 page
        
        # Update scene with analysis results
        update_data = {
            'characters': analysis.get('characters', []),
            'props': analysis.get('props', []),
            'wardrobe': analysis.get('wardrobe', []),
            'special_fx': analysis.get('special_fx', []),
            'vehicles': analysis.get('vehicles', []),
            'makeup_hair': analysis.get('makeup_hair', []),
            'locations': analysis.get('locations', []),
            'sound': analysis.get('sound', []),
            'atmosphere': analysis.get('atmosphere', ''),
            'description': analysis.get('description', ''),
            'page_length_eighths': page_length_eighths,
            'analysis_status': 'complete',
            # Story Days (Phase 1)
            'time_transition': analysis.get('time_transition', ''),
            'is_new_story_day': analysis.get('is_new_story_day', False),
            'story_day_confidence': 0.7,
            'timeline_code': analysis.get('timeline_code', 'PRESENT'),
        }
        
        supabase.table('scenes').update(update_data).eq('id', scene_id).execute()
        
        # Story Days: Trigger cascade recalculation from this scene onward
        story_day_fields = {}
        try:
            from services.story_day_service import recalculate_story_days
            recalculate_story_days(scene['script_id'], start_from_order=current_order or 0)
            # Re-read scene to get recalculated story_day values
            refreshed = supabase.table('scenes').select(
                'story_day, story_day_label, is_new_story_day, story_day_is_locked, '
                'story_day_is_manual, story_day_confidence, timeline_code, time_transition'
            ).eq('id', scene_id).single().execute()
            if refreshed.data:
                story_day_fields = refreshed.data
        except Exception as recalc_err:
            print(f"[StoryDays] Recalculation after single-scene analysis failed (non-fatal): {recalc_err}")
        
        return jsonify({
            'message': 'Scene analyzed successfully',
            'scene_id': scene_id,
            'analysis': {**analysis, **story_day_fields}
        }), 200
        
    except Exception as e:
        print(f"Error analyzing scene: {e}")
        import traceback
        traceback.print_exc()
        # Update status to error
        try:
            supabase.table('scenes').update({'analysis_status': 'error'}).eq('id', scene_id).execute()
        except:
            pass
        return jsonify({'error': str(e)}), 500


def analyze_scene_with_gemini(scene_text, setting, known_speakers=None, shot_type=None, location_hierarchy=None, prev_scene_context=None):
    """
    Use Gemini to analyze a single scene.
    
    Phase 2 optimization: When known_speakers are provided (from ScreenPy
    grammar parsing), the prompt is optimized — AI only extracts non-speaking
    characters from action lines instead of guessing ALL characters.
    
    Story Days (Phase 1): When prev_scene_context is provided, injects the
    previous scene's header so the AI can detect day transitions.
    """
    import google.generativeai as genai
    from services.entity_resolver import merge_to_character_list
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    has_speakers = known_speakers and len(known_speakers) > 0
    
    # Build previous scene context block (Story Days Phase 1)
    prev_context_block = ""
    if prev_scene_context:
        prev_context_block = (
            f"\nCONTEXT — PREVIOUS SCENE:\n"
            f"  Scene {prev_scene_context.get('scene_number_original', prev_scene_context.get('scene_number', '?'))}: "
            f"{prev_scene_context.get('int_ext', '')}. {prev_scene_context.get('setting', '')} "
            f"- {prev_scene_context.get('time_of_day', '')}\n"
            f"  Summary: {prev_scene_context.get('description', 'N/A')}\n"
        )
    else:
        prev_context_block = "\nCONTEXT: This is the FIRST scene of the script.\n"
    
    # Build pre-extracted context block
    context_block = ""
    context_lines = []
    if has_speakers:
        speaker_list = ", ".join(sorted(known_speakers.keys()))
        context_lines.append(f"KNOWN SPEAKING CHARACTERS (already identified from dialogue): [{speaker_list}]")
    if shot_type:
        context_lines.append(f"SHOT TYPE: {shot_type}")
    if location_hierarchy and len(location_hierarchy) > 1:
        context_lines.append(f"LOCATION HIERARCHY: {' > '.join(location_hierarchy)}")
    if context_lines:
        context_block = "\nPRE-EXTRACTED CONTEXT:\n" + "\n".join(context_lines) + "\n"
    
    # Build character section based on available data
    if has_speakers:
        char_instruction = (
            "- NON_SPEAKING_CHARACTERS: Characters in ACTION LINES who are NOT in the known speakers list. UPPERCASE names only.\n"
            "- EXTRAS: Background actors, crowd requirements"
        )
        char_json = '    "non_speaking_characters": ["BOUNCER", "WAITRESS #2"],'
    else:
        char_instruction = (
            "- CHARACTERS: ALL character names that appear or speak (UPPERCASE names only)\n"
            "- EXTRAS: Background actors, crowd requirements"
        )
        char_json = '    "characters": ["CHARACTER1", "CHARACTER2"],'
    
    prompt = f"""Analyze this screenplay scene and extract detailed breakdown information.

Scene Setting: {setting}
{prev_context_block}{context_block}
Scene Text:
{scene_text[:8000]}

Extract and return ONLY valid JSON:
{char_instruction}
- PROPS: Physical objects characters interact with
- WARDROBE: Specific clothing/costumes mentioned
- SPECIAL_FX: Visual/practical effects
- VEHICLES: All vehicles appearing
- MAKEUP_HAIR: Makeup, hair styling requirements
- LOCATIONS: Specific areas/rooms within the main setting
- SOUND: Sound effects, music cues, ambient sounds
- ATMOSPHERE: Mood, lighting, weather
- DESCRIPTION: 2-3 sentence summary

**STORY TIMELINE:**
- TIME_TRANSITION: Any time-transition cue at the START of this scene relative to the previous scene
  (e.g., "THE NEXT MORNING", "CONTINUOUS", "LATER THAT DAY", "THREE WEEKS LATER", "SAME TIME", "MOMENTS LATER")
  Return empty string "" if no transition is indicated.
- IS_NEW_STORY_DAY: true/false — Does this scene start a NEW narrative day compared to the previous scene?
  Consider: NIGHT→MORNING = new day, CONTINUOUS = same day, explicit "NEXT DAY" = new day, DAY→NIGHT = usually same day.
- TIMELINE_CODE: One of: PRESENT, FLASHBACK, DREAM, FANTASY, MONTAGE, TITLE_CARD
  Default to PRESENT unless scene text explicitly indicates a flashback, dream, etc.

Return format:
{{
{char_json}
    "extras": [],
    "props": ["prop1", "prop2"],
    "wardrobe": ["Character: description"],
    "special_fx": [],
    "vehicles": [],
    "makeup_hair": [],
    "locations": [],
    "sound": [],
    "atmosphere": "Description of mood",
    "description": "Scene summary",
    "time_transition": "",
    "is_new_story_day": false,
    "timeline_code": "PRESENT"
}}

IMPORTANT:
- Characters in UPPERCASE
- Only include items ACTUALLY in the scene text
- If a category doesn't apply, use empty array []
- Return ONLY the JSON, no markdown or extra text
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.3)
        )
        
        response_text = response.text.strip()
        
        # Clean up response
        import re
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        result = json.loads(response_text)
        
        # Phase 2: Entity resolution — merge speakers with AI characters
        if has_speakers:
            ai_characters = result.get('characters', []) + result.get('non_speaking_characters', [])
            result['characters'] = merge_to_character_list(known_speakers, ai_characters)
        
        # Normalize story day fields
        result['time_transition'] = result.get('time_transition', '')
        result['is_new_story_day'] = bool(result.get('is_new_story_day', False))
        result['timeline_code'] = result.get('timeline_code', 'PRESENT')
        
        return result
        
    except Exception as e:
        print(f"Gemini analysis error: {e}")
        fallback = {
            'characters': [],
            'props': [],
            'wardrobe': [],
            'special_fx': [],
            'vehicles': [],
            'makeup_hair': [],
            'locations': [],
            'sound': [],
            'atmosphere': '',
            'description': f'Analysis failed: {str(e)}',
            'time_transition': '',
            'is_new_story_day': False,
            'timeline_code': 'PRESENT',
        }
        # Still merge speakers into fallback if available
        if has_speakers:
            fallback['characters'] = merge_to_character_list(known_speakers, [])
        return fallback


@supabase_bp.route('/api/scripts/<script_id>/analyze/bulk', methods=['POST'])
def analyze_bulk_scenes(script_id):
    """
    Analyze all pending scenes for a script.
    Returns immediately (202 Accepted), analysis happens in background thread.
    
    Flow:
    1. Get all pending scenes for the script
    2. Create a job record in analysis_jobs table
    3. Start background thread to process scenes one-by-one
    4. Return immediately with job info
    5. Frontend polls for progress via existing status endpoints
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get all pending + error scenes (error scenes can be retried)
        result = supabase.table('scenes').select('id, scene_number').eq('script_id', script_id).in_('analysis_status', ['pending', 'error']).order('scene_number').execute()
        
        pending_scenes = result.data
        pending_count = len(pending_scenes)
        
        if pending_count == 0:
            return jsonify({'message': 'No pending scenes to analyze', 'queued': 0}), 200
        
        # Create job record for tracking
        job_id = str(uuid.uuid4())
        scene_ids = [s['id'] for s in pending_scenes]
        
        job_data = {
            'id': job_id,
            'script_id': script_id,
            'job_type': 'bulk_scene_analysis',
            'status': 'queued',
            'progress': 0,
            'result_summary': f'Queued {pending_count} scenes for analysis'
        }
        
        supabase.table('analysis_jobs').insert(job_data).execute()
        print(f"✓ Created bulk analysis job {job_id} for {pending_count} scenes")
        
        # Start background thread for processing
        thread = threading.Thread(
            target=process_bulk_analysis_job,
            args=(job_id, script_id, scene_ids),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'message': 'Bulk analysis started',
            'job_id': job_id,
            'total': pending_count,
            'status': 'queued'
        }), 202  # 202 Accepted - processing will happen asynchronously
        
    except Exception as e:
        print(f"Error starting bulk analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def process_bulk_analysis_job(job_id, script_id, scene_ids):
    """
    Background worker to process scenes one-by-one.
    
    - Retries each scene up to 3 times with exponential backoff on rate-limit errors
    - Wraps progress updates in try/except so they can't crash the loop
    - Adaptive delay: increases wait time after consecutive failures
    - Updates job status to 'completed' or 'failed' at end
    """
    total = len(scene_ids)
    analyzed = 0
    failed = 0
    base_delay = 3  # seconds between successful calls
    current_delay = base_delay
    max_retries = 3
    
    print(f"🚀 Starting bulk analysis job {job_id}: {total} scenes")
    
    try:
        # Update job status to processing
        supabase.table('analysis_jobs').update({
            'status': 'processing',
            'result_summary': f'Processing scene 1 of {total}',
            'started_at': 'now()'
        }).eq('id', job_id).execute()
        
        for i, scene_id in enumerate(scene_ids):
            scene_success = False
            
            for attempt in range(1, max_retries + 1):
                try:
                    analyze_scene_internal(scene_id)
                    analyzed += 1
                    scene_success = True
                    current_delay = base_delay  # Reset delay on success
                    break
                    
                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = any(kw in error_str for kw in ['429', 'resource_exhausted', 'rate', 'quota'])
                    
                    if is_rate_limit and attempt < max_retries:
                        backoff = base_delay * (2 ** attempt)  # 6s, 12s, 24s
                        print(f"  ⏳ Scene {scene_id} rate-limited (attempt {attempt}/{max_retries}), retrying in {backoff}s...")
                        time.sleep(backoff)
                        current_delay = min(current_delay + 2, 10)  # Increase base delay too
                        continue
                    
                    print(f"  ✗ Scene {scene_id} failed (attempt {attempt}/{max_retries}): {e}")
                    if attempt == max_retries:
                        failed += 1
                        try:
                            supabase.table('scenes').update({'analysis_status': 'error'}).eq('id', scene_id).execute()
                        except:
                            pass
            
            # Update job progress (wrapped in try/except so it can't crash the loop)
            try:
                progress = int(((i + 1) / total) * 100)
                supabase.table('analysis_jobs').update({
                    'progress': progress,
                    'result_summary': f'Analyzed {i + 1} of {total} scenes ({analyzed} success, {failed} failed)'
                }).eq('id', job_id).execute()
            except Exception as progress_err:
                print(f"  ⚠ Progress update failed (non-fatal): {progress_err}")
            
            # Rate limit between scenes (skip after last scene)
            if i < total - 1:
                time.sleep(current_delay)
        
        # Story Days: Trigger full recalculation after bulk analysis completes
        if analyzed > 0:
            try:
                from services.story_day_service import recalculate_story_days
                result = recalculate_story_days(script_id)
                print(f"✓ Story days recalculated: {result.get('total_days', 0)} days, {result.get('scenes_updated', 0)} scenes updated")
            except Exception as recalc_err:
                print(f"⚠ Story days recalculation failed (non-fatal): {recalc_err}")
        
        # Job completed
        final_status = 'completed' if failed == 0 else 'completed_with_errors'
        supabase.table('analysis_jobs').update({
            'status': final_status,
            'progress': 100,
            'result_summary': f'Completed: {analyzed} analyzed, {failed} failed',
            'completed_at': 'now()'
        }).eq('id', job_id).execute()
        
        print(f"✓ Bulk analysis job {job_id} completed: {analyzed}/{total} scenes analyzed")
        
    except Exception as e:
        print(f"✗ Bulk analysis job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            supabase.table('analysis_jobs').update({
                'status': 'failed',
                'error_message': str(e),
                'completed_at': 'now()'
            }).eq('id', job_id).execute()
        except:
            pass


def analyze_scene_internal(scene_id):
    """
    Internal function to analyze a single scene.
    Reuses the same logic as the analyze_scene endpoint but without HTTP response.
    
    Phase 2: Fetches pre-extracted speakers, shot_type, and location_hierarchy
    from the scene record (populated by ScreenPy grammar parser in Phase 1)
    and passes them to the optimized Gemini prompt.
    
    Raises exception on failure (caller handles error).
    """
    # Get scene data
    scene_result = supabase.table('scenes').select('*').eq('id', scene_id).single().execute()
    scene = scene_result.data
    
    if not scene:
        raise ValueError(f"Scene {scene_id} not found")
    
    # Update status to analyzing
    supabase.table('scenes').update({'analysis_status': 'analyzing'}).eq('id', scene_id).execute()
    
    # Get scene text
    scene_text = scene.get('scene_text', '')
    if not scene_text or len(scene_text) < 10:
        # If no scene text, try to get from full script
        script_result = supabase.table('scripts').select('full_text').eq('id', scene['script_id']).single().execute()
        full_text = script_result.data.get('full_text', '')
        
        text_start = scene.get('text_start', 0)
        text_end = scene.get('text_end', len(full_text))
        scene_text = full_text[text_start:text_end] if full_text else ''
    
    if not scene_text:
        supabase.table('scenes').update({'analysis_status': 'error'}).eq('id', scene_id).execute()
        raise ValueError(f"No scene text available for scene {scene_id}")
    
    # Phase 2: Extract pre-parsed data for prompt optimization
    known_speakers = scene.get('speakers') or {}
    if isinstance(known_speakers, str):
        known_speakers = json.loads(known_speakers)
    # Normalize: speakers may be a list of names (from detect_and_create_scenes_v2)
    if isinstance(known_speakers, list):
        known_speakers = {name: {} for name in known_speakers}
    scene_shot_type = scene.get('shot_type')
    scene_location_hierarchy = scene.get('location_hierarchy') or []
    if isinstance(scene_location_hierarchy, str):
        scene_location_hierarchy = json.loads(scene_location_hierarchy)
    
    has_speakers = known_speakers and len(known_speakers) > 0
    opt_label = "optimized" if has_speakers else "full"
    print(f"  → Analyzing scene {scene_id} (prompt={opt_label}, speakers={len(known_speakers) if known_speakers else 0})")
    
    # Story Days Phase 1: Fetch previous scene for context injection
    prev_scene_context = None
    current_order = scene.get('scene_order') or scene.get('scene_number', 0)
    if current_order and current_order > 1:
        from db.supabase_client import db as supa_db
        prev_scene = supa_db.get_scene_by_order(scene['script_id'], current_order - 1)
        if prev_scene:
            prev_scene_context = prev_scene
    
    # Call Gemini for analysis with pre-extracted context
    analysis = analyze_scene_with_gemini(
        scene_text, scene.get('setting', ''),
        known_speakers=known_speakers if has_speakers else None,
        shot_type=scene_shot_type,
        location_hierarchy=scene_location_hierarchy,
        prev_scene_context=prev_scene_context,
    )
    
    # Recalculate scene length in eighths with full scene text
    from utils.scene_calculations import calculate_eighths_from_content, calculate_eighths_from_pages
    if scene_text and len(scene_text.strip()) > 50:
        page_length_eighths = calculate_eighths_from_content(scene_text)
    elif scene.get('page_start') and scene.get('page_end'):
        page_length_eighths = calculate_eighths_from_pages(scene.get('page_start'), scene.get('page_end'))
    else:
        page_length_eighths = 8  # Default to 1 page
    
    # Update scene with analysis results
    update_data = {
        'characters': analysis.get('characters', []),
        'props': analysis.get('props', []),
        'wardrobe': analysis.get('wardrobe', []),
        'special_fx': analysis.get('special_fx', []),
        'vehicles': analysis.get('vehicles', []),
        'makeup_hair': analysis.get('makeup_hair', []),
        'locations': analysis.get('locations', []),
        'sound': analysis.get('sound', []),
        'atmosphere': analysis.get('atmosphere', ''),
        'description': analysis.get('description', ''),
        'page_length_eighths': page_length_eighths,
        'analysis_status': 'complete',
        # Story Days (Phase 1)
        'time_transition': analysis.get('time_transition', ''),
        'is_new_story_day': analysis.get('is_new_story_day', False),
        'story_day_confidence': 0.7,
        'timeline_code': analysis.get('timeline_code', 'PRESENT'),
    }
    
    supabase.table('scenes').update(update_data).eq('id', scene_id).execute()
    print(f"  ✓ Scene {scene_id} analyzed")


# ============================================
# Re-extract Metadata Endpoint
# ============================================

@supabase_bp.route('/api/scripts/<script_id>/reextract-metadata', methods=['POST'])
def reextract_metadata(script_id):
    """
    Re-extract metadata from the first page of an existing script.
    Useful for scripts that were uploaded before metadata extraction was improved.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Get script with first page text
        script_result = supabase.table('scripts').select('id, title, full_text').eq('id', script_id).single().execute()
        script = script_result.data
        
        if not script:
            return jsonify({'error': 'Script not found'}), 404
        
        full_text = script.get('full_text', '')
        if not full_text:
            return jsonify({'error': 'No script text available'}), 400
        
        # Extract metadata from first page (approx 4000 chars)
        first_page_text = full_text[:4000]
        metadata = extract_title_page_metadata(first_page_text)
        
        print(f"Re-extracted metadata for {script_id}: {metadata}")
        
        # Update script with new metadata
        update_data = {}
        if metadata.get('writers'):
            update_data['writer_name'] = metadata['writers']
        if metadata.get('phone'):
            update_data['contact_phone'] = metadata['phone']
        if metadata.get('email'):
            update_data['contact_email'] = metadata['email']
        if metadata.get('draft_version'):
            update_data['draft_version'] = metadata['draft_version']
        if metadata.get('production_company'):
            update_data['production_company'] = metadata['production_company']
        if metadata.get('copyright'):
            update_data['copyright_year'] = metadata['copyright']
        if metadata.get('wga_registration'):
            update_data['wga_registration'] = metadata['wga_registration']
        
        if update_data:
            supabase.table('scripts').update(update_data).eq('id', script_id).execute()
            print(f"✓ Updated script {script_id} with: {update_data}")
        
        return jsonify({
            'message': 'Metadata re-extracted successfully',
            'script_id': script_id,
            'extracted': metadata,
            'updated_fields': list(update_data.keys())
        }), 200
        
    except Exception as e:
        print(f"Error re-extracting metadata: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# Department Items (Breakdown CRUD) Endpoints
# ============================================

@supabase_bp.route('/api/scripts/<script_id>/items', methods=['GET'])
def get_script_items(script_id):
    """
    Get all department_items for an entire script (across all scenes).
    Used by Stripboard and other views that need merged breakdown data.
    
    Query params:
    - include_removed: 'true' to include soft-deleted items (default: false)
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        query = supabase.table('department_items').select(
            'id, script_id, scene_id, item_type, item_name, status, source_type, priority'
        ).eq('script_id', script_id)
        
        include_removed = request.args.get('include_removed', 'false').lower() == 'true'
        if not include_removed:
            query = query.neq('status', 'removed')
        
        result = query.order('created_at', desc=True).execute()
        
        return jsonify({'items': result.data or []}), 200
        
    except Exception as e:
        print(f"Error getting script items: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/items', methods=['GET'])
def get_scene_items(script_id, scene_id):
    """
    Get all department_items for a scene, optionally filtered by item_type.
    
    Query params:
    - item_type: Filter by category (e.g., 'characters', 'props', 'wardrobe')
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        query = supabase.table('department_items').select(
            '*, departments!department_items_department_id_fkey(code, name, color, icon), '
            'creator:profiles!department_items_created_by_fkey(id, full_name, email, avatar_url), '
            'assignee:profiles!department_items_assigned_to_fkey(id, full_name, email, avatar_url)'
        ).eq('script_id', script_id).eq('scene_id', scene_id)
        
        item_type = request.args.get('item_type')
        if item_type:
            query = query.eq('item_type', item_type)
        
        # By default exclude removed items; pass include_removed=true to see them
        include_removed = request.args.get('include_removed', 'false').lower() == 'true'
        if not include_removed:
            query = query.neq('status', 'removed')
        
        result = query.order('created_at', desc=True).execute()
        
        items = []
        for item in result.data:
            dept = item.pop('departments', {}) or {}
            creator = item.pop('creator', {}) or {}
            assignee = item.pop('assignee', {}) or {}
            
            items.append({
                **item,
                'department_code': dept.get('code'),
                'department_name': dept.get('name'),
                'department_color': dept.get('color'),
                'department_icon': dept.get('icon'),
                'creator_name': creator.get('full_name') or (creator.get('email', '').split('@')[0] if creator.get('email') else None),
                'creator_avatar': creator.get('avatar_url'),
                'assignee_name': assignee.get('full_name') or (assignee.get('email', '').split('@')[0] if assignee.get('email') else None),
                'assignee_avatar': assignee.get('avatar_url'),
            })
        
        return jsonify({'items': items}), 200
        
    except Exception as e:
        print(f"Error getting scene items: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/items', methods=['POST'])
@optional_auth
def create_scene_item(script_id, scene_id):
    """
    Create a new breakdown item for a scene.
    
    Body:
    {
        "item_type": "characters" | "props" | "wardrobe" | etc.,
        "item_name": "Item name",
        "description": "Optional description",
        "priority": "normal" | "high" | "low",
        "status": "pending" | "in_progress" | "complete"
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        user_id = get_user_id()
        
        item_name = data.get('item_name', '').strip()
        if not item_name:
            return jsonify({'error': 'item_name is required'}), 400
        
        item_type = data.get('item_type', '').strip()
        if not item_type:
            return jsonify({'error': 'item_type is required'}), 400
        
        # Auto-detect user's department from script_members
        department_id = None
        if user_id:
            try:
                member_result = supabase.table('script_members').select(
                    'department_code'
                ).eq('script_id', script_id).eq('user_id', user_id).single().execute()
                
                if member_result.data and member_result.data.get('department_code'):
                    dept_result = supabase.table('departments').select('id').eq(
                        'code', member_result.data['department_code']
                    ).single().execute()
                    if dept_result.data:
                        department_id = dept_result.data.get('id')
            except Exception as member_err:
                print(f"Note: User not a member, using production dept: {member_err}")
        
        # Fallback to 'production' department
        if not department_id:
            try:
                prod_dept = supabase.table('departments').select('id').eq('code', 'production').single().execute()
                if prod_dept.data:
                    department_id = prod_dept.data['id']
            except:
                pass
        
        if not department_id:
            return jsonify({'error': 'Could not determine department'}), 400
        
        item_data = {
            'script_id': script_id,
            'scene_id': scene_id,
            'department_id': department_id,
            'item_type': item_type,
            'item_name': item_name,
            'description': data.get('description', ''),
            'status': data.get('status', 'pending'),
            'priority': data.get('priority', 'normal'),
            'source_type': 'manual',
            'created_by': user_id,
        }
        
        result = supabase.table('department_items').insert(item_data).execute()
        
        if result.data:
            # Fetch the created item with joins
            created = supabase.table('department_items').select(
                '*, departments!department_items_department_id_fkey(code, name, color, icon), '
                'creator:profiles!department_items_created_by_fkey(id, full_name, email, avatar_url)'
            ).eq('id', result.data[0]['id']).single().execute()
            
            item = created.data
            dept = item.pop('departments', {}) or {}
            creator = item.pop('creator', {}) or {}
            
            return jsonify({
                **item,
                'department_code': dept.get('code'),
                'department_name': dept.get('name'),
                'department_color': dept.get('color'),
                'department_icon': dept.get('icon'),
                'creator_name': creator.get('full_name') or (creator.get('email', '').split('@')[0] if creator.get('email') else None),
                'creator_avatar': creator.get('avatar_url'),
            }), 201
        
        return jsonify({'error': 'Failed to create item'}), 500
        
    except Exception as e:
        print(f"Error creating scene item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/items/<item_id>', methods=['PUT'])
@optional_auth
def update_scene_item(item_id):
    """
    Update a breakdown item.
    
    Body (all optional):
    {
        "item_name": "Updated name",
        "description": "Updated description",
        "status": "pending" | "in_progress" | "complete",
        "priority": "normal" | "high" | "low",
        "assigned_to": "user_uuid" | null,
        "due_date": "2026-03-01" | null
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        
        allowed_fields = ['item_name', 'description', 'status', 'priority', 'assigned_to', 'due_date', 'metadata']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        result = supabase.table('department_items').update(update_data).eq('id', item_id).execute()
        
        if result.data:
            updated = supabase.table('department_items').select(
                '*, departments!department_items_department_id_fkey(code, name, color, icon), '
                'creator:profiles!department_items_created_by_fkey(id, full_name, email, avatar_url), '
                'assignee:profiles!department_items_assigned_to_fkey(id, full_name, email, avatar_url)'
            ).eq('id', item_id).single().execute()
            
            item = updated.data
            dept = item.pop('departments', {}) or {}
            creator = item.pop('creator', {}) or {}
            assignee = item.pop('assignee', {}) or {}
            
            return jsonify({
                **item,
                'department_code': dept.get('code'),
                'department_name': dept.get('name'),
                'department_color': dept.get('color'),
                'department_icon': dept.get('icon'),
                'creator_name': creator.get('full_name') or (creator.get('email', '').split('@')[0] if creator.get('email') else None),
                'creator_avatar': creator.get('avatar_url'),
                'assignee_name': assignee.get('full_name') or (assignee.get('email', '').split('@')[0] if assignee.get('email') else None),
                'assignee_avatar': assignee.get('avatar_url'),
            }), 200
        
        return jsonify({'error': 'Item not found'}), 404
        
    except Exception as e:
        print(f"Error updating item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/remove-ai-item', methods=['PATCH'])
@optional_auth
def remove_ai_item(script_id, scene_id):
    """
    Remove an item from a scene's JSONB breakdown array.
    
    Body:
    {
        "item_type": "vehicles",   // matches the scene column name
        "item_name": "stroller"    // exact string to remove
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        item_type = data.get('item_type', '').strip()
        item_name = data.get('item_name', '').strip()
        
        if not item_type or not item_name:
            return jsonify({'error': 'item_type and item_name are required'}), 400
        
        # Allowed JSONB array columns on scenes table
        allowed_columns = [
            'characters', 'props', 'wardrobe', 'makeup_hair', 'special_fx',
            'vehicles', 'locations', 'sound', 'animals', 'extras', 'stunts', 'speakers'
        ]
        
        if item_type not in allowed_columns:
            return jsonify({'error': f'Invalid item_type: {item_type}'}), 400
        
        # Fetch current array
        scene_result = supabase.table('scenes').select(item_type).eq('id', scene_id).single().execute()
        
        if not scene_result.data:
            return jsonify({'error': 'Scene not found'}), 404
        
        current_items = scene_result.data.get(item_type) or []
        
        # Filter out the item (case-insensitive match for strings)
        updated_items = [
            i for i in current_items
            if not (isinstance(i, str) and i.strip().lower() == item_name.lower())
        ]
        
        if len(updated_items) == len(current_items):
            return jsonify({'error': 'Item not found in list'}), 404
        
        # Update the scene JSONB
        supabase.table('scenes').update({item_type: updated_items}).eq('id', scene_id).execute()
        
        # Create a tracking record in department_items so the drawer can show strikethrough
        user_id = get_user_id()
        tracking_record = {
            'script_id': script_id,
            'scene_id': scene_id,
            'item_type': item_type,
            'item_name': item_name,
            'status': 'removed',
            'source_type': 'ai_removed',
            'priority': 'normal'
        }
        if user_id:
            tracking_record['created_by'] = user_id
        
        # Try to find the user's department for this script
        if user_id:
            try:
                member_result = supabase.table('script_members').select('department_id').eq('script_id', script_id).eq('user_id', user_id).limit(1).execute()
                if member_result.data and member_result.data[0].get('department_id'):
                    tracking_record['department_id'] = member_result.data[0]['department_id']
            except Exception:
                pass
        
        try:
            supabase.table('department_items').insert(tracking_record).execute()
        except Exception as track_err:
            print(f"Warning: Could not create tracking record: {track_err}")
        
        return jsonify({
            'message': 'Item removed',
            'item_type': item_type,
            'item_name': item_name,
            'remaining_items': updated_items
        }), 200
        
    except Exception as e:
        print(f"Error removing AI item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/items/<item_id>', methods=['DELETE'])
@optional_auth
def delete_scene_item(item_id):
    """Soft-delete a breakdown item by setting status to 'removed'."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        supabase.table('department_items').update({'status': 'removed'}).eq('id', item_id).execute()
        return jsonify({'message': 'Item removed successfully'}), 200
    except Exception as e:
        print(f"Error removing item: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# Department Notes Endpoints
# ============================================

@supabase_bp.route('/api/departments', methods=['GET'])
def get_departments():
    """Get all departments with their colors and icons."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('departments').select('*').order('sort_order').execute()
        return jsonify({'departments': result.data}), 200
    except Exception as e:
        print(f"Error getting departments: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/notes', methods=['GET'])
def get_script_notes(script_id):
    """
    Get all notes for a script.
    
    Query params:
    - department: Filter by department code (e.g., 'director', 'vfx')
    - scene_id: Filter by scene ID
    - status: Filter by status ('open', 'in_progress', 'resolved')
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        # Build query - include creator profile info
        # Use explicit FK references since there are multiple FKs to departments and profiles
        # Only fetch top-level notes (parent_id is null)
        query = supabase.table('department_notes').select(
            '*, departments!department_notes_department_id_fkey(code, name, color, icon), profiles!department_notes_created_by_fkey(id, full_name, email, avatar_url)'
        ).eq('script_id', script_id).is_('parent_id', 'null')
        
        # Apply filters
        department_code = request.args.get('department')
        scene_id = request.args.get('scene_id')
        status = request.args.get('status')
        
        if department_code:
            # Get department ID from code
            dept_result = supabase.table('departments').select('id').eq('code', department_code).single().execute()
            if dept_result.data:
                query = query.eq('department_id', dept_result.data['id'])
        
        if scene_id:
            query = query.eq('scene_id', scene_id)
        
        if status:
            query = query.eq('status', status)
        
        result = query.order('created_at', desc=True).execute()
        
        # Format response and fetch replies for each note
        notes = []
        for note in result.data:
            dept = note.pop('departments', {}) or {}
            creator = note.pop('profiles', {}) or {}
            
            # Fetch replies for this note
            replies_result = supabase.table('department_notes').select(
                '*, profiles!department_notes_created_by_fkey(id, full_name, email, avatar_url)'
            ).eq('parent_id', note['id']).order('created_at', desc=False).execute()
            
            replies = []
            for reply in replies_result.data:
                reply_creator = reply.pop('profiles', {}) or {}
                replies.append({
                    **reply,
                    'creator_name': reply_creator.get('full_name') or reply_creator.get('email', '').split('@')[0] if reply_creator else None,
                    'creator_avatar': reply_creator.get('avatar_url')
                })
            
            notes.append({
                **note,
                'department_code': dept.get('code'),
                'department_name': dept.get('name'),
                'department_color': dept.get('color'),
                'department_icon': dept.get('icon'),
                'creator_name': creator.get('full_name') or creator.get('email', '').split('@')[0] if creator else None,
                'creator_avatar': creator.get('avatar_url'),
                'replies': replies,
                'reply_count': len(replies)
            })
        
        return jsonify({'notes': notes}), 200
        
    except Exception as e:
        print(f"Error getting notes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/notes', methods=['POST'])
@optional_auth
def create_note(script_id):
    """
    Create a new note. User's department is auto-detected from script_members.
    
    Body:
    {
        "scene_id": "uuid" (optional),
        "note_type": "characters" | "props" | "wardrobe" | etc.,
        "content": "Note content"
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        user_id = get_user_id()  # Get authenticated user ID
        
        # Validate content
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'error': 'content is required'}), 400
        
        # Auto-detect user's department from script_members
        department_id = None
        department_code = None
        if user_id:
            try:
                # script_members uses department_code, not department_id
                member_result = supabase.table('script_members').select(
                    'department_code'
                ).eq('script_id', script_id).eq('user_id', user_id).single().execute()
                
                if member_result.data and member_result.data.get('department_code'):
                    department_code = member_result.data['department_code']
                    # Get department ID from code
                    dept_result = supabase.table('departments').select('id').eq('code', department_code).single().execute()
                    if dept_result.data:
                        department_id = dept_result.data.get('id')
            except Exception as member_err:
                print(f"Note: User not a member of this script, using production department: {member_err}")
        
        # Fallback to 'production' department if user has no membership
        if not department_id:
            try:
                prod_dept = supabase.table('departments').select('id, code').eq('code', 'production').single().execute()
                if prod_dept.data:
                    department_id = prod_dept.data['id']
                    department_code = 'production'
            except:
                # Create production department if it doesn't exist
                new_dept = supabase.table('departments').insert({
                    'code': 'production',
                    'name': 'Production',
                    'color': '#6B7280',
                    'icon': 'briefcase'
                }).execute()
                if new_dept.data:
                    department_id = new_dept.data[0]['id']
                    department_code = 'production'
        
        # Build note data
        note_data = {
            'script_id': script_id,
            'department_id': department_id,
            'scene_id': data.get('scene_id'),
            'created_by': user_id,  # Track who created the note
            'note_type': data.get('note_type', 'general'),
            'content': content,
            'status': 'open'
        }
        
        result = supabase.table('department_notes').insert(note_data).execute()
        
        if result.data:
            # Fetch the created note with department and creator info
            created_note = supabase.table('department_notes').select(
                '*, departments!department_notes_department_id_fkey(code, name, color, icon), profiles!department_notes_created_by_fkey(id, full_name, email, avatar_url)'
            ).eq('id', result.data[0]['id']).single().execute()
            
            note = created_note.data
            dept = note.pop('departments', {}) or {}
            creator = note.pop('profiles', {}) or {}
            
            return jsonify({
                **note,
                'department_code': dept.get('code'),
                'department_name': dept.get('name'),
                'department_color': dept.get('color'),
                'department_icon': dept.get('icon'),
                'creator_name': creator.get('full_name') or creator.get('email', '').split('@')[0] if creator else None,
                'creator_avatar': creator.get('avatar_url')
            }), 201
        
        return jsonify({'error': 'Failed to create note'}), 500
        
    except Exception as e:
        print(f"Error creating note: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/notes/<note_id>/replies', methods=['POST'])
@optional_auth
def create_reply(note_id):
    """
    Create a reply to an existing note.
    
    Body:
    {
        "content": "Reply content"
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        user_id = get_user_id()
        
        # Validate content
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'error': 'content is required'}), 400
        
        # Get the parent note to inherit script_id, scene_id, note_type
        parent_note = supabase.table('department_notes').select(
            'script_id, scene_id, note_type, department_id'
        ).eq('id', note_id).single().execute()
        
        if not parent_note.data:
            return jsonify({'error': 'Parent note not found'}), 404
        
        # Get user's department (same logic as create_note)
        department_id = parent_note.data.get('department_id')
        if user_id:
            try:
                member_result = supabase.table('script_members').select(
                    'department_code'
                ).eq('script_id', parent_note.data['script_id']).eq('user_id', user_id).single().execute()
                
                if member_result.data and member_result.data.get('department_code'):
                    dept_result = supabase.table('departments').select('id').eq('code', member_result.data['department_code']).single().execute()
                    if dept_result.data:
                        department_id = dept_result.data.get('id')
            except:
                pass
        
        # Build reply data
        reply_data = {
            'script_id': parent_note.data['script_id'],
            'scene_id': parent_note.data.get('scene_id'),
            'note_type': parent_note.data.get('note_type', 'general'),
            'department_id': department_id,
            'parent_id': note_id,
            'created_by': user_id,
            'content': content,
            'status': 'open'
        }
        
        result = supabase.table('department_notes').insert(reply_data).execute()
        
        if result.data:
            # Fetch the created reply with creator info
            created_reply = supabase.table('department_notes').select(
                '*, profiles!department_notes_created_by_fkey(id, full_name, email, avatar_url)'
            ).eq('id', result.data[0]['id']).single().execute()
            
            reply = created_reply.data
            creator = reply.pop('profiles', {}) or {}
            
            return jsonify({
                **reply,
                'creator_name': creator.get('full_name') or creator.get('email', '').split('@')[0] if creator else None,
                'creator_avatar': creator.get('avatar_url')
            }), 201
        
        return jsonify({'error': 'Failed to create reply'}), 500
        
    except Exception as e:
        print(f"Error creating reply: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    """Get a single note by ID."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('department_notes').select(
            '*, departments!department_notes_department_id_fkey(code, name, color, icon)'
        ).eq('id', note_id).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Note not found'}), 404
        
        note = result.data
        dept = note.pop('departments', {})
        
        return jsonify({
            **note,
            'department_code': dept.get('code'),
            'department_name': dept.get('name'),
            'department_color': dept.get('color'),
            'department_icon': dept.get('icon')
        }), 200
        
    except Exception as e:
        print(f"Error getting note: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/notes/<note_id>', methods=['PUT'])
def update_note(note_id):
    """
    Update a note.
    
    Body (all optional):
    {
        "title": "Updated title",
        "content": "Updated content",
        "note_type": "budget",
        "priority": "high",
        "status": "in_progress",
        "structured_data": {}
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        
        # Only allow updating certain fields
        allowed_fields = ['title', 'content', 'note_type', 'priority', 'status', 'structured_data']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        result = supabase.table('department_notes').update(update_data).eq('id', note_id).execute()
        
        if result.data:
            # Fetch updated note with department and creator info
            updated_note = supabase.table('department_notes').select(
                '*, departments!department_notes_department_id_fkey(code, name, color, icon), profiles!department_notes_created_by_fkey(id, full_name, email, avatar_url)'
            ).eq('id', note_id).single().execute()
            
            note = updated_note.data
            dept = note.pop('departments', {}) or {}
            creator = note.pop('profiles', {}) or {}
            
            return jsonify({
                **note,
                'department_code': dept.get('code'),
                'department_name': dept.get('name'),
                'department_color': dept.get('color'),
                'department_icon': dept.get('icon'),
                'creator_name': creator.get('full_name') or creator.get('email', '').split('@')[0] if creator else None,
                'creator_avatar': creator.get('avatar_url')
            }), 200
        
        return jsonify({'error': 'Note not found'}), 404
        
    except Exception as e:
        print(f"Error updating note: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/notes/<note_id>/status', methods=['PATCH'])
@optional_auth
def update_note_status(note_id):
    """
    Quick endpoint to toggle note status.
    
    Body:
    {
        "status": "open" | "resolved"
    }
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['open', 'resolved', 'in_progress']:
            return jsonify({'error': 'Invalid status. Must be: open, resolved, or in_progress'}), 400
        
        user_id = get_user_id()
        
        # Update status and track who resolved it
        update_data = {
            'status': new_status,
            'updated_at': 'now()'
        }
        
        result = supabase.table('department_notes').update(update_data).eq('id', note_id).execute()
        
        if result.data:
            # Fetch updated note
            updated_note = supabase.table('department_notes').select(
                '*, departments!department_notes_department_id_fkey(code, name, color, icon), profiles!department_notes_created_by_fkey(id, full_name, email, avatar_url)'
            ).eq('id', note_id).single().execute()
            
            note = updated_note.data
            dept = note.pop('departments', {}) or {}
            creator = note.pop('profiles', {}) or {}
            
            return jsonify({
                **note,
                'department_code': dept.get('code'),
                'department_name': dept.get('name'),
                'department_color': dept.get('color'),
                'department_icon': dept.get('icon'),
                'creator_name': creator.get('full_name') or creator.get('email', '').split('@')[0] if creator else None,
                'creator_avatar': creator.get('avatar_url')
            }), 200
        
        return jsonify({'error': 'Note not found'}), 404
        
    except Exception as e:
        print(f"Error updating note status: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a note."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        supabase.table('department_notes').delete().eq('id', note_id).execute()
        return jsonify({'message': 'Note deleted successfully'}), 200
    except Exception as e:
        print(f"Error deleting note: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scenes/<scene_id>/notes', methods=['GET'])
def get_scene_notes(scene_id):
    """Get all notes for a specific scene, grouped by department."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('department_notes').select(
            '*, departments!department_notes_department_id_fkey(code, name, color, icon)'
        ).eq('scene_id', scene_id).order('created_at', desc=True).execute()
        
        # Group by department
        by_department = {}
        for note in result.data:
            dept = note.pop('departments', {})
            dept_code = dept.get('code', 'unknown')
            
            if dept_code not in by_department:
                by_department[dept_code] = {
                    'department_code': dept_code,
                    'department_name': dept.get('name'),
                    'department_color': dept.get('color'),
                    'department_icon': dept.get('icon'),
                    'notes': []
                }
            
            by_department[dept_code]['notes'].append(note)
        
        return jsonify({
            'scene_id': scene_id,
            'departments': list(by_department.values()),
            'total_notes': len(result.data)
        }), 200
        
    except Exception as e:
        print(f"Error getting scene notes: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# Phase 3: Revision Import Endpoints
# ============================================

@supabase_bp.route('/api/scripts/<script_id>/versions', methods=['GET'])
@require_auth
def get_script_versions(script_id):
    """Get all versions/revisions of a script."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('script_versions').select('*').eq(
            'script_id', script_id
        ).order('version_number', desc=True).execute()
        
        return jsonify({
            'script_id': script_id,
            'versions': result.data or [],
            'total': len(result.data) if result.data else 0
        }), 200
        
    except Exception as e:
        print(f"Error getting script versions: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/versions/import', methods=['POST'])
@require_auth
def import_revision(script_id):
    """
    Import a new revision of a script.
    
    Expects multipart form data with:
    - file: PDF file
    - revision_color: Color for this revision (white, blue, pink, etc.)
    - notes: Optional notes about this revision
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        from services.revision_service import (
            extract_scenes_from_pdf,
            diff_script_versions,
            create_version_record,
            apply_revision_changes
        )
        
        # Check for file
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        revision_color = request.form.get('revision_color', 'white')
        notes = request.form.get('notes', '')
        apply_changes = request.form.get('apply_changes', 'false').lower() == 'true'
        
        # Save file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Extract scenes from new PDF
            new_scenes = extract_scenes_from_pdf(tmp_path)
            
            # Get existing scenes
            existing_result = supabase.table('scenes').select('*').eq(
                'script_id', script_id
            ).order('scene_order').execute()
            
            old_scenes = existing_result.data or []
            
            # Calculate diff
            diffs = diff_script_versions(old_scenes, new_scenes)
            
            # Prepare response
            diff_summary = {
                'added': len([d for d in diffs if d.change_type.value == 'added']),
                'modified': len([d for d in diffs if d.change_type.value == 'modified']),
                'removed': len([d for d in diffs if d.change_type.value == 'removed']),
                'unchanged': len([d for d in diffs if d.change_type.value == 'unchanged']),
                'total_new_scenes': len(new_scenes),
                'total_old_scenes': len(old_scenes)
            }
            
            if apply_changes:
                # Create version record
                version = create_version_record(
                    supabase, script_id, revision_color, 
                    pdf_path=None, notes=notes
                )
                
                if version:
                    # Apply changes to database
                    stats = apply_revision_changes(
                        supabase, script_id, version['id'], 
                        diffs, new_scenes
                    )
                    
                    return jsonify({
                        'success': True,
                        'version': version,
                        'diff_summary': diff_summary,
                        'applied_stats': stats,
                        'message': f"Revision imported successfully. {stats['added']} added, {stats['modified']} modified, {stats['removed']} removed."
                    }), 200
                else:
                    return jsonify({'error': 'Failed to create version record'}), 500
            else:
                # Preview mode - just return the diff
                return jsonify({
                    'success': True,
                    'preview': True,
                    'diff_summary': diff_summary,
                    'diffs': [d.to_dict() for d in diffs],
                    'new_scenes': new_scenes,
                    'message': 'Preview generated. Set apply_changes=true to apply.'
                }), 200
                
        finally:
            # Clean up temp file
            import os
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
    except Exception as e:
        print(f"Error importing revision: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/versions/<version_id>/diff', methods=['GET'])
@require_auth
def get_version_diff(script_id, version_id):
    """
    Get the diff for a specific version.
    
    Query params:
    - compare_to: Optional version ID to compare against (defaults to previous version)
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        from services.revision_service import get_version_diff as get_diff
        
        compare_to = request.args.get('compare_to')
        
        diff_data = get_diff(supabase, script_id, version_id, compare_to)
        
        return jsonify({
            'script_id': script_id,
            'version_id': version_id,
            'compare_to': compare_to,
            'changes': diff_data
        }), 200
        
    except Exception as e:
        print(f"Error getting version diff: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/versions/<version_id>', methods=['GET'])
@require_auth
def get_version_details(script_id, version_id):
    """Get details of a specific version."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    
    try:
        result = supabase.table('script_versions').select('*').eq(
            'id', version_id
        ).single().execute()
        
        if not result.data:
            return jsonify({'error': 'Version not found'}), 404
        
        # Get scene history for this version
        history_result = supabase.table('scene_history').select(
            '*, scenes!scene_history_scene_id_fkey(scene_number, setting)'
        ).eq('version_id', version_id).execute()
        
        return jsonify({
            'version': result.data,
            'changes': history_result.data or []
        }), 200
        
    except Exception as e:
        print(f"Error getting version details: {e}")
        return jsonify({'error': str(e)}), 500
