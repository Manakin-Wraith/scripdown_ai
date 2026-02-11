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
from typing import Dict, List, Optional
import google.generativeai as genai
from utils.scene_calculations import calculate_eighths_from_content
from services.entity_resolver import merge_to_character_list

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


def enhance_scene(
    scene_text: str,
    scene_header: Dict,
    known_speakers: Optional[Dict[str, int]] = None,
    shot_type: Optional[str] = None,
    location_hierarchy: Optional[List[str]] = None,
    prev_scene_context: Optional[Dict] = None,
) -> Dict:
    """
    Use AI to extract detailed breakdown from a single scene.
    
    Phase 2 optimization: When known_speakers are provided (from ScreenPy
    grammar parsing), the prompt is smaller and more focused — AI only
    extracts non-speaking characters from action lines instead of guessing
    ALL characters from scratch.
    
    Story Days (Phase 1): When prev_scene_context is provided, the prompt
    includes the previous scene's header/time_of_day so the AI can detect
    day transitions (e.g., NIGHT→MORNING = new day).
    
    Args:
        scene_text: The full text of the scene
        scene_header: Dict with scene_number, setting, int_ext, time_of_day
        known_speakers: Dict of speaker_name → dialogue_count from grammar
                       parsing. If provided, character extraction is optimized.
        shot_type: Pre-extracted shot type (e.g., "CLOSE ON", "WIDE SHOT")
        location_hierarchy: Pre-extracted location hierarchy list
        prev_scene_context: Dict with previous scene's header info for story
                           day detection. Keys: scene_number, int_ext, setting,
                           time_of_day, description. None if first scene.
    
    Returns:
        Dict with characters, props, wardrobe, vehicles, atmosphere, description,
        plus story day fields: time_transition, is_new_story_day, timeline_code.
        When known_speakers are provided, characters list is the merged result
        of speakers + AI-extracted non-speaking characters.
    """
    # Truncate very long scenes
    max_chars = 4000
    if len(scene_text) > max_chars:
        scene_text = scene_text[:max_chars] + "\n[... scene continues ...]"
    
    has_speakers = known_speakers and len(known_speakers) > 0
    
    prompt = _build_prompt(
        scene_text, scene_header,
        known_speakers=known_speakers,
        shot_type=shot_type,
        location_hierarchy=location_hierarchy,
        prev_scene_context=prev_scene_context,
    )
    
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
        
        # Phase 2: Entity resolution — merge speakers with AI characters
        if has_speakers:
            ai_characters = result.get('characters', []) + result.get('non_speaking_characters', [])
            merged_characters = merge_to_character_list(known_speakers, ai_characters)
        else:
            merged_characters = result.get('characters', [])
        
        # Validate and normalize - include all new fields
        return {
            'characters': merged_characters,
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
            # Story Days (Phase 1)
            'time_transition': result.get('time_transition', ''),
            'is_new_story_day': bool(result.get('is_new_story_day', False)),
            'timeline_code': result.get('timeline_code', 'PRESENT'),
        }
        
    except json.JSONDecodeError as e:
        print(f"[Enhancer] JSON parse error: {e}")
        fallback = extract_fallback(scene_text)
        if has_speakers:
            fallback['characters'] = merge_to_character_list(known_speakers, fallback['characters'])
        return fallback
    except Exception as e:
        print(f"[Enhancer] AI error: {e}")
        raise


def _build_prompt(
    scene_text: str,
    scene_header: Dict,
    known_speakers: Optional[Dict[str, int]] = None,
    shot_type: Optional[str] = None,
    location_hierarchy: Optional[List[str]] = None,
    prev_scene_context: Optional[Dict] = None,
) -> str:
    """
    Build the AI prompt, optimized based on available pre-extracted data.
    
    When known_speakers are available:
    - Replaces full character extraction with focused non-speaking character extraction
    - Injects known speaker context to reduce hallucination
    - ~30-40% smaller prompt = fewer tokens = faster + cheaper
    
    Story Days (Phase 1): When prev_scene_context is provided, injects the
    previous scene's header so the AI can detect day transitions.
    """
    has_speakers = known_speakers and len(known_speakers) > 0
    
    # Build context header
    header_line = (
        f"Scene {scene_header.get('scene_number', '?')}: "
        f"{scene_header.get('int_ext', '')}. "
        f"{scene_header.get('setting', '')} - "
        f"{scene_header.get('time_of_day', '')}"
    )
    
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
    context_lines = []
    if has_speakers:
        speaker_list = ", ".join(sorted(known_speakers.keys()))
        context_lines.append(f"KNOWN SPEAKING CHARACTERS (already identified from dialogue): [{speaker_list}]")
    if shot_type:
        context_lines.append(f"SHOT TYPE: {shot_type}")
    if location_hierarchy and len(location_hierarchy) > 1:
        context_lines.append(f"LOCATION HIERARCHY: {' > '.join(location_hierarchy)}")
    
    context_block = ""
    if context_lines:
        context_block = "\nPRE-EXTRACTED CONTEXT:\n" + "\n".join(context_lines) + "\n"
    
    # Build character extraction section based on available data
    if has_speakers:
        character_section = (
            "**NON-SPEAKING CHARACTERS:**\n"
            "1. NON_SPEAKING_CHARACTERS: Characters who appear in ACTION LINES but are NOT in the known speakers list above. "
            "Look for named characters in stage directions, descriptions, and action paragraphs. UPPERCASE names only.\n"
            "2. EXTRAS: Background actors, crowd requirements (e.g., \"Restaurant patrons (8)\", \"Crowd (20-30)\")"
        )
    else:
        character_section = (
            "**CAST & CHARACTERS:**\n"
            "1. CHARACTERS: ALL character names that appear or speak (UPPERCASE names only)\n"
            "2. EXTRAS: Background actors, crowd requirements (e.g., \"Restaurant patrons (8)\", \"Crowd (20-30)\")"
        )
    
    # Build JSON schema based on available data
    if has_speakers:
        char_json = '    "non_speaking_characters": ["BOUNCER", "WAITRESS #2"],'
    else:
        char_json = '    "characters": ["CHARACTER1", "CHARACTER2"],'
    
    prompt = f"""Analyze this screenplay scene and extract production breakdown details.

SCENE HEADER:
{header_line}
{prev_context_block}{context_block}
SCENE TEXT:
{scene_text}

Extract the following (be thorough but accurate - only include what's ACTUALLY in the scene):

{character_section}

**PROPS & SET DRESSING:**
3. PROPS: Physical objects characters interact with or that are important

**WARDROBE DEPARTMENT:**
4. WARDROBE: Specific clothing, costumes, accessories mentioned

**MAKEUP & HAIR DEPARTMENT:**
5. MAKEUP_HAIR: Makeup, hair styling, special makeup effects (e.g., "Bruised face", "Period hairstyle")

**SPECIAL EFFECTS DEPARTMENT:**
6. SPECIAL_FX: Visual/practical effects (e.g., "Gunshot squib", "Rain effect", "Explosion")

**STUNTS DEPARTMENT:**
7. STUNTS: Stunt requirements, fight choreography, dangerous actions

**VEHICLES & TRANSPORTATION:**
8. VEHICLES: ALL vehicles appearing or mentioned

**ANIMALS & WRANGLERS:**
9. ANIMALS: ALL animals appearing

**SOUND DEPARTMENT:**
10. SOUND: Sound effects, music cues, ambient sounds

**SCENE DESCRIPTIONS:**
11. DESCRIPTION: 2-3 sentence summary of what happens
12. ACTION_DESCRIPTION: Summary of physical action
13. EMOTIONAL_TONE: Emotional mood
14. TECHNICAL_NOTES: Camera, lighting, equipment requirements
15. ATMOSPHERE: Overall mood, lighting, weather details

**STORY TIMELINE:**
16. TIME_TRANSITION: Any time-transition cue at the START of this scene relative to the previous scene
    (e.g., "THE NEXT MORNING", "CONTINUOUS", "LATER THAT DAY", "THREE WEEKS LATER", "SAME TIME", "MOMENTS LATER")
    Return empty string "" if no transition is indicated.
17. IS_NEW_STORY_DAY: true/false — Does this scene start a NEW narrative day compared to the previous scene?
    Consider: NIGHT→MORNING = new day, CONTINUOUS = same day, explicit "NEXT DAY" = new day, DAY→NIGHT = usually same day.
18. TIMELINE_CODE: One of: PRESENT, FLASHBACK, DREAM, FANTASY, MONTAGE, TITLE_CARD
    Default to PRESENT unless scene text explicitly indicates a flashback, dream, etc.

Return ONLY valid JSON in this exact format:
{{
{char_json}
    "extras": ["Restaurant patrons (8)"],
    "props": ["coffee cup", "laptop"],
    "wardrobe": ["Business suit"],
    "makeup_hair": ["Natural makeup"],
    "special_fx": ["Rain on window"],
    "stunts": [],
    "vehicles": ["BMW sedan"],
    "animals": [],
    "sound": ["Ambient coffee shop noise"],
    "description": "What happens in this scene",
    "action_description": "Physical actions characters perform",
    "emotional_tone": "Tense and melancholic",
    "technical_notes": "Close-ups for emotional beats",
    "atmosphere": "Intimate, slightly uncomfortable",
    "time_transition": "",
    "is_new_story_day": false,
    "timeline_code": "PRESENT"
}}

IMPORTANT:
- Only include items ACTUALLY in the scene text
- Character names in UPPERCASE
- If a category has nothing, use empty array [] or empty string ""
- Return ONLY the JSON, no markdown formatting
"""
    return prompt


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
        # Story Days (Phase 1) — safe defaults for fallback
        'time_transition': '',
        'is_new_story_day': False,
        'timeline_code': 'PRESENT',
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
            content_hash,
            time_transition, is_new_story_day, story_day_confidence, timeline_code
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        candidate.get('content_hash', ''),
        # Story Days (Phase 1)
        enhancement.get('time_transition', ''),
        1 if enhancement.get('is_new_story_day') else 0,
        0.7,  # Default confidence for AI-determined values
        enhancement.get('timeline_code', 'PRESENT'),
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
        
        # Phase 2: Extract pre-parsed data from candidate for prompt optimization
        known_speakers = candidate.get('speaker_list') or candidate.get('speakers')
        if isinstance(known_speakers, str):
            known_speakers = json.loads(known_speakers)
        candidate_shot_type = candidate.get('shot_type')
        candidate_location_hierarchy = candidate.get('location_hierarchy')
        if isinstance(candidate_location_hierarchy, str):
            candidate_location_hierarchy = json.loads(candidate_location_hierarchy)
        
        has_speakers = known_speakers and len(known_speakers) > 0
        opt_label = "optimized" if has_speakers else "full"
        
        # Story Days Phase 1: Fetch previous scene for context injection
        prev_scene_context = None
        current_order = candidate.get('scene_order', 0)
        if current_order > 1:
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT scene_number_original, int_ext, setting, time_of_day, description
                FROM scenes
                WHERE script_id = ? AND scene_number = ?
                ORDER BY scene_number ASC
                LIMIT 1
            """, (script_id, current_order - 1))
            prev_row = cursor.fetchone()
            if prev_row:
                prev_scene_context = {
                    'scene_number_original': prev_row[0],
                    'int_ext': prev_row[1] or '',
                    'setting': prev_row[2] or '',
                    'time_of_day': prev_row[3] or '',
                    'description': prev_row[4] or 'N/A',
                }
        
        # Enhance with AI
        print(f"[Enhancer] Enhancing scene {candidate['scene_number_original']} (pages {candidate['page_start']}-{candidate['page_end']}, prompt={opt_label})")
        enhancement = enhance_scene(
            scene_text, scene_header,
            known_speakers=known_speakers if has_speakers else None,
            shot_type=candidate_shot_type,
            location_hierarchy=candidate_location_hierarchy,
            prev_scene_context=prev_scene_context,
        )
        
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
    
    # Story Days Phase 1: Trigger recalculation after all candidates processed
    if processed > 0:
        try:
            from services.story_day_service import recalculate_story_days
            sd_result = recalculate_story_days(str(script_id))
            print(f"[Enhancer] Story days recalculated: {sd_result.get('total_days', 0)} days")
        except Exception as sd_err:
            print(f"[Enhancer] Story days recalculation skipped (non-fatal): {sd_err}")
    
    return {
        'processed': processed,
        'failed': failed,
        'skipped': skipped,
        'total': total
    }
