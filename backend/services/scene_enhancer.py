"""
Scene Enhancer - AI-powered scene detail extraction.

This module handles Pass 2 of the extraction pipeline:
- Takes a scene candidate with known boundaries
- Uses AI to extract: characters, props, wardrobe, vehicles, atmosphere
- Stores the enhanced scene in the database

KEY DESIGN DECISIONS:
- One AI call per scene (small, focused prompts)
- Idempotent: Checks content hash before processing
- Resumable: Each scene is independent
- Rate-limit aware: Respects Gemini API limits
"""

import json
import time
import os
from typing import Dict, Optional
import google.generativeai as genai
from utils.scene_calculations import calculate_eighths_from_content

# Rate limiting
RATE_LIMIT_SECONDS = 4  # Gemini free tier: 15 RPM = 4 seconds between calls
_last_request_time = 0


def get_gemini_model():
    """Get configured Gemini model."""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key or api_key == 'your_api_key_here':
        raise ValueError("GEMINI_API_KEY not configured")
    
    genai.configure(api_key=api_key)
    # Use gemini-2.5-flash - latest model with good quota
    return genai.GenerativeModel('gemini-2.5-flash')


def rate_limit_wait():
    """Wait if needed to respect rate limits."""
    global _last_request_time
    
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_SECONDS:
        wait_time = RATE_LIMIT_SECONDS - elapsed
        print(f"[Enhancer] Rate limit: waiting {wait_time:.1f}s")
        time.sleep(wait_time)
    
    _last_request_time = time.time()


def enhance_scene(scene_text: str, scene_header: Dict) -> Dict:
    """
    Use AI to extract detailed breakdown from a single scene.
    
    Args:
        scene_text: The full text of the scene
        scene_header: Dict with scene_number, setting, int_ext, time_of_day
    
    Returns:
        Dict with characters, props, wardrobe, vehicles, atmosphere, description
    """
    # Truncate very long scenes
    max_chars = 4000
    if len(scene_text) > max_chars:
        scene_text = scene_text[:max_chars] + "\n[... scene continues ...]"
    
    prompt = f"""
Analyze this screenplay scene and extract COMPLETE production breakdown details for all departments.

SCENE HEADER:
Scene {scene_header.get('scene_number', '?')}: {scene_header.get('int_ext', '')}. {scene_header.get('setting', '')} - {scene_header.get('time_of_day', '')}

SCENE TEXT:
{scene_text}

Extract the following (be thorough but accurate - only include what's ACTUALLY in the scene):

**CAST & CHARACTERS:**
1. CHARACTERS: ALL character names that appear or speak (UPPERCASE names only)
2. EXTRAS: Background actors, crowd requirements (e.g., "Restaurant patrons (8)", "Crowd (20-30)")

**PROPS & SET DRESSING:**
3. PROPS: Physical objects characters interact with or that are important

**WARDROBE DEPARTMENT:**
4. WARDROBE: Specific clothing, costumes, accessories mentioned

**MAKEUP & HAIR DEPARTMENT:**
5. MAKEUP_HAIR: Makeup, hair styling, special makeup effects (e.g., "Bruised face", "Period hairstyle")

**SPECIAL EFFECTS DEPARTMENT:**
6. SPECIAL_FX: Visual/practical effects (e.g., "Gunshot squib", "Rain effect", "Explosion")

**STUNTS DEPARTMENT:**
7. STUNTS: Stunt requirements, fight choreography, dangerous actions (e.g., "Car crash", "Fight choreography", "Fall from height")

**VEHICLES & TRANSPORTATION:**
8. VEHICLES: ALL vehicles appearing or mentioned (e.g., "Police car", "Motorcycle")

**ANIMALS & WRANGLERS:**
9. ANIMALS: ALL animals appearing (e.g., "German Shepherd", "Horses (3)")

**LOCATIONS:**
10. LOCATIONS: Specific areas, rooms, or sub-locations within main setting (e.g., "kitchen", "rooftop")

**SOUND DEPARTMENT:**
11. SOUND: Sound effects, music cues, ambient sounds (e.g., "Thunder SFX", "Jazz music", "Gunshots")

**SCENE DESCRIPTIONS:**
12. DESCRIPTION: 2-3 sentence summary of what happens
13. ACTION_DESCRIPTION: Summary of physical action (what characters DO physically)
14. EMOTIONAL_TONE: Emotional mood (e.g., "Tense", "Romantic", "Suspenseful")
15. TECHNICAL_NOTES: Camera, lighting, equipment requirements (e.g., "Crane shot", "Low-light")
16. ATMOSPHERE: Overall mood, lighting, weather details

Return ONLY valid JSON in this exact format:
{{
    "characters": ["CHARACTER1", "CHARACTER2"],
    "extras": ["Restaurant patrons (8)"],
    "props": ["coffee cup", "laptop"],
    "wardrobe": ["Business suit"],
    "makeup_hair": ["Natural makeup"],
    "special_fx": ["Rain on window"],
    "stunts": [],
    "vehicles": ["BMW sedan"],
    "animals": [],
    "locations": ["kitchen", "living room"],
    "sound": ["Ambient coffee shop noise"],
    "description": "What happens in this scene",
    "action_description": "Physical actions characters perform",
    "emotional_tone": "Tense and melancholic",
    "technical_notes": "Close-ups for emotional beats",
    "atmosphere": "Intimate, slightly uncomfortable"
}}

IMPORTANT:
- Only include items ACTUALLY in the scene text
- Character names in UPPERCASE
- Separate stunts from special_fx (stunts = performed by people, special_fx = technical effects)
- If a category has nothing, use empty array [] or empty string ""
- Return ONLY the JSON, no markdown formatting
"""
    
    try:
        rate_limit_wait()
        
        model = get_gemini_model()
        response = model.generate_content(prompt)
        
        # Parse response
        response_text = response.text.strip()
        
        # Clean up markdown if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])
        
        result = json.loads(response_text)
        
        # Validate and normalize - include all new fields
        return {
            'characters': result.get('characters', []),
            'extras': result.get('extras', []),
            'props': result.get('props', []),
            'wardrobe': result.get('wardrobe', []),
            'makeup_hair': result.get('makeup_hair', []),
            'special_fx': result.get('special_fx', []),
            'stunts': result.get('stunts', []),
            'vehicles': result.get('vehicles', []),
            'animals': result.get('animals', []),
            'locations': result.get('locations', []),
            'sound': result.get('sound', []),
            'description': result.get('description', ''),
            'action_description': result.get('action_description', ''),
            'emotional_tone': result.get('emotional_tone', ''),
            'technical_notes': result.get('technical_notes', ''),
            'atmosphere': result.get('atmosphere', ''),
        }
        
    except json.JSONDecodeError as e:
        print(f"[Enhancer] JSON parse error: {e}")
        return extract_fallback(scene_text)
    except Exception as e:
        print(f"[Enhancer] AI error: {e}")
        raise


def extract_fallback(scene_text: str) -> Dict:
    """
    Fallback extraction using regex when AI fails.
    Better than nothing!
    """
    import re
    
    # Find character names (UPPERCASE words that look like names)
    char_pattern = r'\b([A-Z][A-Z]+(?:\s+[A-Z]+)?)\b'
    potential_chars = re.findall(char_pattern, scene_text)
    
    # Filter out common non-character words
    exclude = {'INT', 'EXT', 'DAY', 'NIGHT', 'CONTINUOUS', 'LATER', 'CUT', 'FADE', 
               'THE', 'AND', 'BUT', 'FOR', 'WITH', 'FROM', 'ANGLE', 'CLOSE', 'WIDE'}
    characters = [c for c in set(potential_chars) if c not in exclude and len(c) > 1]
    
    return {
        'characters': characters[:20],  # Limit to 20
        'extras': [],
        'props': [],
        'wardrobe': [],
        'makeup_hair': [],
        'special_fx': [],
        'stunts': [],
        'vehicles': [],
        'animals': [],
        'locations': [],
        'sound': [],
        'description': 'Scene details extracted with fallback method.',
        'action_description': '',
        'emotional_tone': '',
        'technical_notes': '',
        'atmosphere': '',
    }


def save_enhanced_scene(script_id: int, candidate: Dict, enhancement: Dict, db_conn, scene_text: str = None) -> int:
    """
    Save the enhanced scene to the database.
    
    Args:
        script_id: Script ID
        candidate: Scene candidate dict
        enhancement: Enhanced scene data from AI
        db_conn: Database connection
        scene_text: Full scene text for eighths calculation
    
    Returns the scene_id of the saved scene.
    """
    cursor = db_conn.cursor()
    
    # Build the full setting string
    setting = f"{candidate['setting']}"
    if candidate.get('int_ext'):
        setting = f"{candidate['setting']} - {candidate['int_ext']}"
    if candidate.get('time_of_day'):
        setting = f"{setting} - {candidate['time_of_day']}"
    
    # Calculate scene length in eighths
    if scene_text:
        page_length_eighths = calculate_eighths_from_content(scene_text)
    else:
        # Fallback: estimate from page range
        from utils.scene_calculations import calculate_eighths_from_pages
        page_length_eighths = calculate_eighths_from_pages(
            candidate.get('page_start'),
            candidate.get('page_end')
        )
    
    cursor.execute("""
        INSERT INTO scenes (
            script_id, scene_number, scene_number_original,
            page_start, page_end, page_length_eighths,
            setting, description,
            characters, props, special_fx, wardrobe,
            makeup_hair, vehicles, animals, extras, stunts,
            locations, sound, atmosphere,
            action_description, emotional_tone, technical_notes, sound_notes,
            content_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        script_id,
        candidate['scene_order'],  # Sequential number for ordering
        candidate['scene_number_original'],  # Original from script
        candidate['page_start'],
        candidate['page_end'],
        page_length_eighths,
        setting,
        enhancement.get('description', ''),
        json.dumps(enhancement.get('characters', [])),
        json.dumps(enhancement.get('props', [])),
        json.dumps(enhancement.get('special_fx', [])),
        json.dumps(enhancement.get('wardrobe', [])),
        json.dumps(enhancement.get('makeup_hair', [])),
        json.dumps(enhancement.get('vehicles', [])),
        json.dumps(enhancement.get('animals', [])),
        json.dumps(enhancement.get('extras', [])),
        json.dumps(enhancement.get('stunts', [])),
        json.dumps(enhancement.get('locations', [])),
        json.dumps(enhancement.get('sound', [])),
        enhancement.get('atmosphere', ''),
        enhancement.get('action_description', ''),
        enhancement.get('emotional_tone', ''),
        enhancement.get('technical_notes', ''),
        enhancement.get('sound', ''),  # sound_notes uses sound field
        candidate.get('content_hash', '')
    ))
    
    scene_id = cursor.lastrowid
    
    # Update candidate status
    cursor.execute("""
        UPDATE scene_candidates 
        SET status = 'completed', processed_at = CURRENT_TIMESTAMP
        WHERE candidate_id = ?
    """, (candidate['candidate_id'],))
    
    db_conn.commit()
    
    return scene_id


def mark_candidate_failed(candidate_id: int, error_message: str, db_conn):
    """Mark a scene candidate as failed."""
    cursor = db_conn.cursor()
    
    cursor.execute("""
        UPDATE scene_candidates 
        SET status = 'failed', error_message = ?, processed_at = CURRENT_TIMESTAMP
        WHERE candidate_id = ?
    """, (error_message, candidate_id))
    
    db_conn.commit()


def process_scene_candidate(script_id: int, candidate: Dict, db_conn) -> Optional[int]:
    """
    Process a single scene candidate.
    
    1. Check if already processed (idempotency)
    2. Get scene text
    3. Enhance with AI
    4. Save to database
    
    Returns scene_id if successful, None if skipped or failed.
    """
    from services.extraction_pipeline import check_already_processed, get_scene_text
    
    # Check idempotency
    if check_already_processed(script_id, candidate['content_hash'], db_conn):
        print(f"[Enhancer] Scene {candidate['scene_number_original']} already processed, skipping")
        return None
    
    try:
        # Get scene text
        scene_text = get_scene_text(
            script_id, 
            candidate['text_start'], 
            candidate['text_end'], 
            db_conn
        )
        
        if not scene_text:
            raise ValueError("Could not retrieve scene text")
        
        # Build header info
        scene_header = {
            'scene_number': candidate['scene_number_original'],
            'int_ext': candidate['int_ext'],
            'setting': candidate['setting'],
            'time_of_day': candidate['time_of_day'],
        }
        
        # Enhance with AI
        print(f"[Enhancer] Enhancing scene {candidate['scene_number_original']} (pages {candidate['page_start']}-{candidate['page_end']})")
        enhancement = enhance_scene(scene_text, scene_header)
        
        # Save to database (pass scene_text for eighths calculation)
        scene_id = save_enhanced_scene(script_id, candidate, enhancement, db_conn, scene_text)
        
        print(f"[Enhancer] Saved scene {candidate['scene_number_original']} as scene_id {scene_id}")
        return scene_id
        
    except Exception as e:
        print(f"[Enhancer] Failed to process scene {candidate['scene_number_original']}: {e}")
        mark_candidate_failed(candidate['candidate_id'], str(e), db_conn)
        return None


def process_all_candidates(script_id: int, db_conn, progress_callback=None) -> Dict:
    """
    Process all pending scene candidates for a script.
    
    Args:
        script_id: The script to process
        db_conn: Database connection
        progress_callback: Optional function(current, total, scene_num) for progress updates
    
    Returns:
        Summary dict with counts
    """
    from services.extraction_pipeline import get_pending_candidates
    
    candidates = get_pending_candidates(script_id, db_conn)
    total = len(candidates)
    
    if total == 0:
        print(f"[Enhancer] No pending candidates for script {script_id}")
        return {'processed': 0, 'failed': 0, 'skipped': 0}
    
    print(f"[Enhancer] Processing {total} scene candidates for script {script_id}")
    
    processed = 0
    failed = 0
    skipped = 0
    
    for i, candidate in enumerate(candidates):
        if progress_callback:
            progress_callback(i + 1, total, candidate['scene_number_original'])
        
        result = process_scene_candidate(script_id, candidate, db_conn)
        
        if result is None:
            # Check if it was skipped (already exists) or failed
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT status FROM scene_candidates WHERE candidate_id = ?",
                (candidate['candidate_id'],)
            )
            row = cursor.fetchone()
            if row and row[0] == 'failed':
                failed += 1
            else:
                skipped += 1
        else:
            processed += 1
    
    return {
        'processed': processed,
        'failed': failed,
        'skipped': skipped,
        'total': total
    }
