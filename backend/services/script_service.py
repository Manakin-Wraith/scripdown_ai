import os
import json
from werkzeug.utils import secure_filename
from utils.pdf_parser import parse_pdf
from utils.metadata_extractor import extract_metadata
from services.gemini_service import analyze_script
from services.langextract_service import (
    extract_with_langextract,
    save_extractions_to_supabase,
    generate_visualization
)
from db.db_connection import get_db

UPLOAD_FOLDER = 'uploads'


def process_script_v2(file):
    """
    Process uploaded script using the new page-based pipeline.
    
    Phase 1 (Synchronous):
    1. Save the file
    2. Parse PDF with page awareness
    3. Detect scene headers (regex)
    4. Create scene candidates
    5. Extract cover page metadata
    6. Save to DB
    
    Returns script_id and summary of what was found.
    """
    from services.extraction_pipeline import (
        parse_pdf_with_pages, 
        build_scene_candidates,
        save_pages_to_db,
        save_scene_candidates_to_db,
        run_migration
    )
    
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # Parse PDF with page awareness
    print(f"[Upload] Parsing PDF with page awareness: {filename}")
    pages, full_text = parse_pdf_with_pages(file_path)
    print(f"[Upload] Parsed {len(pages)} pages")
    
    # Build scene candidates from detected headers
    candidates = build_scene_candidates(pages, full_text)
    print(f"[Upload] Found {len(candidates)} scene candidates")
    
    # Extract cover page metadata (from first page)
    metadata = extract_metadata(file_path)
    print(f"[Upload] Extracted metadata: {metadata}")

    # Save script to Database
    db = get_db()
    
    # Run migration to ensure new tables exist
    run_migration(db)
    
    cursor = db.cursor()
    user_id = 1  # MVP: no auth yet
    
    query = """
        INSERT INTO scripts (
            user_id, script_name, script_text,
            writer_name, writer_email, writer_phone,
            draft_version, draft_date, copyright_info,
            wga_registration, additional_credits,
            analysis_status, analysis_progress
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0)
    """
    cursor.execute(query, (
        user_id, 
        filename, 
        full_text,
        metadata.get('writer_name'),
        metadata.get('writer_email'),
        metadata.get('writer_phone'),
        metadata.get('draft_version'),
        metadata.get('draft_date'),
        metadata.get('copyright_info'),
        metadata.get('wga_registration'),
        metadata.get('additional_credits')
    ))
    db.commit()
    
    script_id = cursor.lastrowid
    cursor.close()
    
    # Save pages and candidates
    pages_saved = save_pages_to_db(script_id, pages, db)
    candidates_saved = save_scene_candidates_to_db(script_id, candidates, db)
    
    print(f"[Upload] Script {script_id}: {pages_saved} pages, {candidates_saved} candidates saved")
    
    return {
        'script_id': script_id,
        'filename': filename,
        'total_pages': len(pages),
        'scene_candidates': len(candidates),
        'metadata': metadata,
        'status': 'ready_for_analysis'
    }


def process_script(file):
    """
    Process the uploaded script (legacy method, still works).
    
    1. Save the file.
    2. Parse PDF text.
    3. Extract cover page metadata.
    4. Save to DB.
    Note: AI analysis is now done separately via /analyze_script endpoint
    """
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # Parse PDF
    script_text = parse_pdf(file_path)
    
    # Extract cover page metadata
    metadata = extract_metadata(file_path)
    print(f"Extracted metadata: {metadata}")

    # Save script to Database with metadata
    db = get_db()
    cursor = db.cursor()
    
    # Assuming user_id is 1 for MVP (no auth yet)
    user_id = 1 
    
    query = """
        INSERT INTO scripts (
            user_id, script_name, script_text,
            writer_name, writer_email, writer_phone,
            draft_version, draft_date, copyright_info,
            wga_registration, additional_credits
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (
        user_id, 
        filename, 
        script_text,
        metadata.get('writer_name'),
        metadata.get('writer_email'),
        metadata.get('writer_phone'),
        metadata.get('draft_version'),
        metadata.get('draft_date'),
        metadata.get('copyright_info'),
        metadata.get('wga_registration'),
        metadata.get('additional_credits')
    ))
    db.commit()
    
    script_id = cursor.lastrowid
    cursor.close()
    
    return script_id

def analyze_script_async(script_id):
    """
    Analyze script with Gemini AI in background.
    Returns number of scenes extracted.
    """
    db = get_db()
    cursor = db.cursor()
    
    # Get script text
    cursor.execute("SELECT script_text FROM scripts WHERE script_id = ?", (script_id,))
    row = cursor.fetchone()
    
    if not row:
        cursor.close()
        raise ValueError(f"Script {script_id} not found")
    
    script_text = row[0]
    cursor.close()
    
    # Analyze with Gemini AI
    try:
        analysis = analyze_script(script_text)
        
        # Save scenes to database
        scene_count = 0
        if 'scenes' in analysis and analysis['scenes']:
            for scene_data in analysis['scenes']:
                save_scene(script_id, scene_data)
                scene_count += 1
            
            print(f"Saved {scene_count} scenes for script {script_id}")
        
        return scene_count
        
    except Exception as e:
        print(f"Warning: Gemini analysis failed: {e}")
        raise

def save_scene(script_id, scene_data):
    """Save scene data to database with detailed breakdown."""
    db = get_db()
    cursor = db.cursor()
    
    query = """
        INSERT INTO scenes (
            script_id, scene_number, setting, description, 
            characters, props, special_fx, wardrobe, 
            makeup_hair, vehicles, atmosphere
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    cursor.execute(query, (
        script_id,
        scene_data.get('scene_number', 0),
        scene_data.get('setting', ''),
        scene_data.get('description', ''),
        json.dumps(scene_data.get('characters', [])),
        json.dumps(scene_data.get('props', [])),
        json.dumps(scene_data.get('special_fx', [])),
        json.dumps(scene_data.get('wardrobe', [])),
        json.dumps(scene_data.get('makeup_hair', [])),
        json.dumps(scene_data.get('vehicles', [])),
        scene_data.get('atmosphere', '')
    ))
    
    db.commit()
    cursor.close()


def process_script_with_langextract(script_id, script_text, supabase_client):
    """
    Process script using LangExtract for structured extraction.
    This replaces the current Gemini service with LangExtract.
    
    Args:
        script_id: UUID of the script (Supabase)
        script_text: Full script text
        supabase_client: Supabase client instance
        
    Returns:
        Dictionary with extraction results and statistics
    """
    print(f"[LangExtract] Starting extraction for script {script_id}")
    
    try:
        # Run LangExtract
        extractions = extract_with_langextract(script_text)
        print(f"[LangExtract] Extracted {len(extractions)} elements")
        
        # Save to database
        saved_count = save_extractions_to_supabase(script_id, extractions, supabase_client)
        print(f"[LangExtract] Saved {saved_count} extractions")
        
        # Generate visualization
        html_viz = generate_visualization(script_id, script_text, extractions, supabase_client)
        print(f"[LangExtract] Generated visualization ({len(html_viz)} bytes)")
        
        # NOTE: aggregate_extractions_to_scenes() removed — extraction_metadata is now
        # the single source of truth. See docs/rich_update.md for details.
        
        # Update script status
        supabase_client.table('scripts').update({
            'analysis_status': 'complete',
            'analysis_progress': 100
        }).eq('id', script_id).execute()
        
        return {
            'success': True,
            'extractions_count': len(extractions),
            'saved_count': saved_count,
            'visualization_size': len(html_viz),
            'status': 'complete'
        }
        
    except Exception as e:
        print(f"[LangExtract] Processing failed: {str(e)}")
        
        # Update script status to failed
        supabase_client.table('scripts').update({
            'analysis_status': 'failed',
            'analysis_progress': 0
        }).eq('id', script_id).execute()
        
        raise


