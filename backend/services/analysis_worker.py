"""
Analysis Worker - Background processor for AI analysis jobs.

This worker:
- Polls the job queue for pending work
- Processes jobs with chunking for large scripts
- Handles rate limiting for Gemini API
- Updates progress in real-time
"""

import json
import time
import threading
import re
import os
import google.generativeai as genai
import sqlite3

# Direct database path for worker (avoids Flask context issues)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'script_breakdown.db')

def get_worker_db():
    """Get database connection for worker (outside Flask context)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================
# Configuration
# ============================================

MAX_SCENES_PER_REQUEST = 15  # Optimal chunk size for Gemini
RATE_LIMIT_SECONDS = 35      # Seconds between API calls (free tier)
WORKER_POLL_INTERVAL = 2     # Seconds between queue checks

_last_request_time = 0
_worker_running = False
_worker_thread = None


# ============================================
# Gemini API Helpers
# ============================================

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
    current_time = time.time()
    elapsed = current_time - _last_request_time
    
    if elapsed < RATE_LIMIT_SECONDS:
        wait_time = RATE_LIMIT_SECONDS - elapsed
        print(f"[Worker] Rate limiting: waiting {wait_time:.1f}s")
        time.sleep(wait_time)
    
    _last_request_time = time.time()


def call_gemini(prompt, temperature=0.7):
    """Make a rate-limited call to Gemini API."""
    rate_limit_wait()
    
    model = get_gemini_model()
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=temperature)
    )
    
    response_text = response.text.strip()
    response_text = re.sub(r'^```json\s*', '', response_text)
    response_text = re.sub(r'\s*```$', '', response_text)
    
    return json.loads(response_text)


# ============================================
# Worker-specific DB functions (avoid Flask context)
# ============================================

def worker_get_next_job():
    """
    Get the next job to process.
    
    IMPORTANT: Jobs that depend on scene extraction must wait for it to complete.
    Priority order:
    1. scene_extraction (legacy) or scene_enhancement (v2) - must complete first
    2. overview, story_arc, characters, locations - depend on scenes existing
    """
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # First, check for any scene_extraction or scene_enhancement jobs that are queued
        # These must run before other jobs
        cursor.execute("""
            SELECT job_id, script_id, job_type, target_id, retry_count, max_retries
            FROM analysis_jobs 
            WHERE status = 'queued' AND job_type IN ('scene_extraction', 'scene_enhancement')
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        
        if row:
            conn.close()
            return {
                'job_id': row[0],
                'script_id': row[1],
                'job_type': row[2],
                'target_id': row[3],
                'retry_count': row[4],
                'max_retries': row[5]
            }
        
        # No extraction jobs queued. Check if any are still processing.
        cursor.execute("""
            SELECT script_id FROM analysis_jobs 
            WHERE status = 'processing' AND job_type IN ('scene_extraction', 'scene_enhancement')
        """)
        
        processing_extraction = cursor.fetchall()
        scripts_with_pending_extraction = [r[0] for r in processing_extraction]
        
        # Get next job, but exclude scripts that have scene_extraction still processing
        if scripts_with_pending_extraction:
            placeholders = ','.join('?' * len(scripts_with_pending_extraction))
            cursor.execute(f"""
                SELECT job_id, script_id, job_type, target_id, retry_count, max_retries
                FROM analysis_jobs 
                WHERE status = 'queued' 
                AND script_id NOT IN ({placeholders})
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
            """, scripts_with_pending_extraction)
        else:
            cursor.execute("""
                SELECT job_id, script_id, job_type, target_id, retry_count, max_retries
                FROM analysis_jobs 
                WHERE status = 'queued'
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
            """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'job_id': row[0],
                'script_id': row[1],
                'job_type': row[2],
                'target_id': row[3],
                'retry_count': row[4],
                'max_retries': row[5]
            }
        return None
        
    except Exception as e:
        print(f"[Worker] Error getting next job: {e}")
        return None


def worker_update_job_status(job_id, status, progress=None, result_summary=None, error_message=None):
    """Update job status with progress message."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        if status == 'processing':
            # Include result_summary during processing for live progress messages
            cursor.execute("""
                UPDATE analysis_jobs 
                SET status = ?, progress = ?, result_summary = ?, started_at = COALESCE(started_at, CURRENT_TIMESTAMP)
                WHERE job_id = ?
            """, (status, progress or 0, result_summary, job_id))
        elif status in ('completed', 'failed'):
            cursor.execute("""
                UPDATE analysis_jobs 
                SET status = ?, progress = ?, result_summary = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (status, progress or 100, result_summary, error_message, job_id))
        else:
            cursor.execute("""
                UPDATE analysis_jobs 
                SET status = ?, progress = ?, result_summary = ?
                WHERE job_id = ?
            """, (status, progress or 0, result_summary, job_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"[Worker] Error updating job status: {e}")


def worker_update_script_status(script_id, status, progress=None):
    """Update script analysis status."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        if status == 'in_progress' and (progress == 0 or progress is None):
            cursor.execute("""
                UPDATE scripts 
                SET analysis_status = ?, analysis_progress = ?, analysis_started_at = CURRENT_TIMESTAMP
                WHERE script_id = ?
            """, (status, progress or 0, script_id))
        elif status == 'complete':
            cursor.execute("""
                UPDATE scripts 
                SET analysis_status = ?, analysis_progress = 100, analysis_completed_at = CURRENT_TIMESTAMP
                WHERE script_id = ?
            """, (status, script_id))
        else:
            cursor.execute("""
                UPDATE scripts 
                SET analysis_status = ?, analysis_progress = ?
                WHERE script_id = ?
            """, (status, progress or 0, script_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"[Worker] Error updating script status: {e}")


def worker_save_character_analysis(script_id, character_name, analysis_data):
    """Save character analysis to cache."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO character_analysis 
            (script_id, character_name, role_type, description, traits, backstory, 
             motivation, arc_summary, scene_breakdown, relationships, is_complete, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        """, (
            script_id,
            character_name,
            analysis_data.get('role_type'),
            analysis_data.get('description'),
            json.dumps(analysis_data.get('traits', [])),
            analysis_data.get('backstory'),
            analysis_data.get('motivation'),
            analysis_data.get('arc_summary'),
            json.dumps(analysis_data.get('scene_breakdown', {})),
            json.dumps(analysis_data.get('relationships', []))
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"[Worker] Error saving character analysis: {e}")


def worker_save_story_arc(script_id, analysis_data):
    """Save story arc analysis to cache."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO story_arc_analysis 
            (script_id, theme, tone, conflict_type, setting_mood, protagonist, 
             antagonist, is_ensemble, narrative_style, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            script_id,
            analysis_data.get('theme'),
            analysis_data.get('tone'),
            analysis_data.get('conflict_type'),
            analysis_data.get('setting_mood'),
            analysis_data.get('protagonist'),
            analysis_data.get('antagonist'),
            1 if analysis_data.get('is_ensemble') else 0,
            analysis_data.get('narrative_style')
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"[Worker] Error saving story arc: {e}")


def worker_save_locations(script_id, result):
    """Save locations analysis to cache."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # Delete existing
        cursor.execute("DELETE FROM script_analysis WHERE script_id = ? AND analysis_type = 'locations'", (script_id,))
        
        # Insert new
        cursor.execute("""
            INSERT INTO script_analysis (script_id, analysis_type, analysis_data)
            VALUES (?, 'locations', ?)
        """, (script_id, json.dumps(result)))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"[Worker] Error saving locations: {e}")


def worker_retry_job(job_id):
    """Increment retry count and re-queue job."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE analysis_jobs 
            SET status = 'queued', 
                retry_count = retry_count + 1,
                error_message = NULL,
                started_at = NULL
            WHERE job_id = ?
        """, (job_id,))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"[Worker] Error retrying job: {e}")


def worker_check_script_completion(script_id):
    """Check if all jobs for a script are complete."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM analysis_jobs 
            WHERE script_id = ?
        """, (script_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            total, completed, failed = row
            
            if completed == total:
                worker_update_script_status(script_id, 'complete', 100)
            elif failed > 0 and (completed + failed) == total:
                worker_update_script_status(script_id, 'partial', int(100 * completed / total) if total > 0 else 0)
            else:
                progress = int(100 * completed / total) if total > 0 else 0
                worker_update_script_status(script_id, 'in_progress', progress)
                
    except Exception as e:
        print(f"[Worker] Error checking completion: {e}")


# ============================================
# Job Processors
# ============================================

def estimate_scene_count(script_text):
    """
    Estimate the number of scenes in a script based on scene headers.
    Returns (estimated_count, scene_headers_found)
    """
    import re
    
    # Common scene header patterns
    patterns = [
        r'\n\s*(?:INT\.|EXT\.|INT/EXT\.|I/E\.)',  # Standard headers
        r'\n\s*\d+\.\s+(?:INT\.|EXT\.)',           # Numbered scenes
        r'\n\s*(?:SCENE|Scene)\s+\d+',              # Explicit scene markers
    ]
    
    headers = []
    for pattern in patterns:
        matches = re.findall(pattern, script_text, re.IGNORECASE)
        headers.extend(matches)
    
    # Remove duplicates and count
    estimated = len(set(headers)) if headers else max(1, len(script_text) // 3000)
    return estimated


def process_scene_extraction_job(job):
    """
    Process scene extraction job - extracts ALL scenes from script in chunks.
    This is the foundation job that must complete before other analysis jobs.
    """
    script_id = job['script_id']
    
    try:
        worker_update_job_status(job['job_id'], 'processing', 5, "Loading script...")
        
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # Get script text
        cursor.execute("SELECT script_text FROM scripts WHERE script_id = ?", (script_id,))
        row = cursor.fetchone()
        
        if not row or not row[0]:
            conn.close()
            worker_update_job_status(job['job_id'], 'failed', error_message="Script text not found")
            return False
        
        script_text = row[0]
        
        # Estimate scene count for progress tracking
        estimated_scenes = estimate_scene_count(script_text)
        print(f"[Worker] Estimated ~{estimated_scenes} scenes in script")
        
        # Clear existing scenes for this script (fresh extraction)
        cursor.execute("DELETE FROM scenes WHERE script_id = ?", (script_id,))
        conn.commit()
        conn.close()
        
        worker_update_job_status(job['job_id'], 'processing', 8, f"Estimated ~{estimated_scenes} scenes to extract")
        
        # Split script into chunks for processing
        chunks = split_script_into_chunks(script_text)
        total_chunks = len(chunks)
        
        print(f"[Worker] Script split into {total_chunks} chunks for extraction")
        worker_update_job_status(job['job_id'], 'processing', 10, f"Processing {total_chunks} chunks (~{estimated_scenes} scenes)")
        
        all_scenes = []
        scene_number = 1
        
        for i, chunk in enumerate(chunks):
            # Check if job was cancelled
            if is_job_cancelled(job['job_id']):
                print(f"[Worker] Job {job['job_id']} was cancelled")
                return False
            
            # Calculate progress (10-90% for extraction)
            progress = 10 + int(80 * ((i + 1) / total_chunks))
            status_msg = f"Chunk {i+1}/{total_chunks} | {len(all_scenes)} scenes extracted"
            worker_update_job_status(job['job_id'], 'processing', progress, status_msg)
            
            # Extract scenes from this chunk
            try:
                chunk_scenes = extract_scenes_from_chunk(chunk, scene_number)
                
                if chunk_scenes:
                    # Save scenes to database with corrected sequential numbering
                    for scene in chunk_scenes:
                        # Override scene number to ensure sequential ordering
                        scene['scene_number'] = scene_number
                        save_extracted_scene(script_id, scene)
                        all_scenes.append(scene)
                        scene_number += 1  # Increment for next scene
                    
            except Exception as e:
                print(f"[Worker] Error extracting chunk {i+1}: {e}")
                # Continue with next chunk, don't fail entire job
                continue
        
        # Final progress update
        worker_update_job_status(job['job_id'], 'processing', 95)
        
        # Update script with scene count
        conn = get_worker_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE scripts SET status = 'analyzed', scene_count = ? WHERE script_id = ?
        """, (len(all_scenes), script_id))
        conn.commit()
        conn.close()
        
        worker_update_job_status(job['job_id'], 'completed', 100, f"Extracted {len(all_scenes)} scenes")
        print(f"[Worker] Scene extraction complete: {len(all_scenes)} scenes")
        return True
        
    except Exception as e:
        print(f"[Worker] Scene extraction job failed: {e}")
        worker_update_job_status(job['job_id'], 'failed', error_message=str(e))
        return False


def split_script_into_chunks(script_text, chunk_size=8000):
    """
    Split script text into chunks for processing.
    Tries to split at scene boundaries when possible.
    """
    # Common scene header patterns
    scene_patterns = [
        r'\n(?:INT\.|EXT\.|INT/EXT\.|I/E\.)',  # Standard scene headers
        r'\n\d+\.\s+(?:INT\.|EXT\.)',           # Numbered scenes
        r'\n(?:SCENE|Scene)\s+\d+',              # Explicit scene markers
    ]
    
    # Find all potential scene boundaries
    boundaries = [0]
    for pattern in scene_patterns:
        for match in re.finditer(pattern, script_text, re.IGNORECASE):
            boundaries.append(match.start())
    
    boundaries = sorted(set(boundaries))
    boundaries.append(len(script_text))
    
    # Create chunks, trying to respect scene boundaries
    chunks = []
    current_start = 0
    
    while current_start < len(script_text):
        # Find the best boundary within chunk_size
        ideal_end = current_start + chunk_size
        
        if ideal_end >= len(script_text):
            # Last chunk
            chunks.append(script_text[current_start:])
            break
        
        # Find nearest boundary before ideal_end
        best_boundary = current_start + chunk_size // 2  # Default to half chunk
        for boundary in boundaries:
            if current_start < boundary <= ideal_end:
                best_boundary = boundary
        
        # Ensure minimum chunk size
        if best_boundary - current_start < chunk_size // 4:
            best_boundary = min(ideal_end, len(script_text))
        
        chunks.append(script_text[current_start:best_boundary])
        current_start = best_boundary
    
    return chunks


def extract_scenes_from_chunk(chunk_text, starting_scene_number):
    """
    Extract scenes from a chunk of script text using Gemini.
    Preserves original scene numbers and page numbers from the script.
    """
    prompt = f"""
Analyze this screenplay excerpt and extract ALL scenes present.

CRITICAL: Preserve the ORIGINAL scene numbers exactly as they appear in the script.
- Scene numbers may be like "1", "1A", "42", "42B", "OMIT", etc.
- If no scene number is visible, use the order starting from {starting_scene_number}

For each scene, provide:
- scene_number_original: The EXACT scene number as written in the script (e.g., "1", "1A", "42", "OMIT")
- scene_number: A sequential integer for ordering (starting from {starting_scene_number})
- page_start: The page number where this scene starts (if visible in the text)
- page_end: The page number where this scene ends (if visible, otherwise same as page_start)
- Setting/Location (e.g., "COFFEE SHOP - INT - DAY")
- Characters present (list ALL character names in UPPERCASE)
- Props (list ALL props, objects, items mentioned or needed)
- Special FX (visual effects, practical effects, stunts)
- Wardrobe notes (costume details, specific clothing mentioned)
- Makeup/Hair notes (any specific requirements)
- Vehicles (cars, bikes, etc.)
- Atmosphere (lighting, weather, mood)
- Description (detailed 2-3 sentence summary of what happens)

Return ONLY valid JSON in this exact format:
{{
    "scenes": [
        {{
            "scene_number": {starting_scene_number},
            "scene_number_original": "1",
            "page_start": 1,
            "page_end": 2,
            "setting": "LOCATION - INT/EXT - TIME",
            "characters": ["CHARACTER1", "CHARACTER2"],
            "props": ["prop1", "prop2"],
            "special_fx": [],
            "wardrobe": [],
            "makeup_hair": [],
            "vehicles": [],
            "atmosphere": "Description of mood/lighting",
            "description": "What happens in this scene"
        }}
    ]
}}

IMPORTANT:
- Extract ALL scenes in this excerpt
- PRESERVE original scene numbers exactly (including letters like "A", "B")
- Include page numbers if they appear in the text
- Be thorough with props, characters, and details
- If a category doesn't apply, use an empty array []
- Look for implied needs (e.g., if someone drinks coffee, include "coffee cup" in props)

Script excerpt:
{chunk_text}

Return only the JSON, no markdown formatting.
"""
    
    result = call_gemini(prompt, temperature=0.3)  # Lower temp for more accuracy
    return result.get('scenes', [])


def save_extracted_scene(script_id, scene_data):
    """Save an extracted scene to the database with original scene/page numbers."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scenes (
                script_id, scene_number, scene_number_original,
                page_start, page_end,
                setting, description, 
                characters, props, special_fx, wardrobe, 
                makeup_hair, vehicles, atmosphere
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            script_id,
            scene_data.get('scene_number', 0),
            scene_data.get('scene_number_original', str(scene_data.get('scene_number', ''))),
            scene_data.get('page_start'),
            scene_data.get('page_end'),
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
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"[Worker] Error saving scene: {e}")


def is_job_cancelled(job_id):
    """Check if a job has been cancelled."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM analysis_jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        return row and row[0] == 'cancelled'
    except:
        return False


def process_overview_job(job):
    """Process overview job - quick stats without AI."""
    script_id = job['script_id']
    
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # Get scene count
        cursor.execute("SELECT COUNT(*) FROM scenes WHERE script_id = ?", (script_id,))
        scene_count = cursor.fetchone()[0]
        
        # Get unique characters
        cursor.execute("SELECT characters FROM scenes WHERE script_id = ?", (script_id,))
        all_chars = set()
        for row in cursor.fetchall():
            if row[0]:
                chars = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                all_chars.update(chars)
        
        # Get unique locations
        cursor.execute("SELECT DISTINCT setting FROM scenes WHERE script_id = ?", (script_id,))
        locations = [row[0] for row in cursor.fetchall() if row[0]]
        
        conn.close()
        
        worker_update_job_status(job['job_id'], 'completed', 100, f"Found {scene_count} scenes, {len(all_chars)} characters")
        return True
        
    except Exception as e:
        print(f"[Worker] Overview job failed: {e}")
        worker_update_job_status(job['job_id'], 'failed', error_message=str(e))
        return False


def process_story_arc_job(job):
    """Process story arc analysis using sampled scenes."""
    script_id = job['script_id']
    
    try:
        worker_update_job_status(job['job_id'], 'processing', 10)
        
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # Get all scenes
        cursor.execute("""
            SELECT scene_number, setting, description, characters 
            FROM scenes WHERE script_id = ? 
            ORDER BY scene_number
        """, (script_id,))
        
        scenes = []
        for row in cursor.fetchall():
            scenes.append({
                'scene_number': row[0],
                'setting': row[1],
                'description': row[2],
                'characters': json.loads(row[3]) if row[3] else []
            })
        
        conn.close()
        
        if not scenes:
            worker_update_job_status(job['job_id'], 'failed', error_message="No scenes found")
            return False
        
        # Sample scenes for story arc analysis
        sampled_scenes = get_act_samples(scenes)
        
        worker_update_job_status(job['job_id'], 'processing', 30)
        
        # Build prompt
        scene_context = "\n".join([
            f"Scene {s['scene_number']} ({s['setting']}): {s['description'][:200]}..."
            for s in sampled_scenes
        ])
        
        prompt = f"""
Analyze the story arc of this screenplay based on these key scenes.

SAMPLED SCENES (from beginning, middle, and end):
{scene_context}

Provide a story arc analysis including:
1. Main theme of the story
2. Overall tone (dark, hopeful, tragic, comedic, etc.)
3. Primary conflict type
4. Setting mood
5. Likely protagonist and antagonist
6. Whether this is an ensemble piece
7. Narrative style

Return ONLY valid JSON:
{{
    "theme": "Main theme of the story",
    "tone": "Overall tone",
    "conflict_type": "man_vs_self|man_vs_man|man_vs_society|man_vs_nature",
    "setting_mood": "Overall mood established by settings",
    "protagonist": "Name of likely protagonist",
    "antagonist": "Name of likely antagonist or null",
    "is_ensemble": true/false,
    "narrative_style": "Description of narrative approach"
}}
"""
        
        result = call_gemini(prompt)
        
        worker_update_job_status(job['job_id'], 'processing', 80)
        
        # Save to cache
        worker_save_story_arc(script_id, result)
        
        worker_update_job_status(job['job_id'], 'completed', 100, f"Theme: {result.get('theme', 'Unknown')}")
        return True
        
    except Exception as e:
        print(f"[Worker] Story arc job failed: {e}")
        worker_update_job_status(job['job_id'], 'failed', error_message=str(e))
        return False


def process_characters_job(job):
    """Process all characters analysis with chunking."""
    script_id = job['script_id']
    
    try:
        worker_update_job_status(job['job_id'], 'processing', 5)
        
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # Get all scenes with characters
        cursor.execute("""
            SELECT scene_number, setting, description, characters 
            FROM scenes WHERE script_id = ? 
            ORDER BY scene_number
        """, (script_id,))
        
        scenes = []
        character_scenes = {}  # character_name -> [scene objects]
        
        for row in cursor.fetchall():
            scene = {
                'scene_number': row[0],
                'setting': row[1],
                'description': row[2],
                'characters': json.loads(row[3]) if row[3] else []
            }
            scenes.append(scene)
            
            for char in scene['characters']:
                if char not in character_scenes:
                    character_scenes[char] = []
                character_scenes[char].append(scene)
        
        conn.close()
        
        if not character_scenes:
            worker_update_job_status(job['job_id'], 'failed', error_message="No characters found")
            return False
        
        # Sort characters by importance (scene count)
        sorted_chars = sorted(
            character_scenes.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        total_chars = len(sorted_chars)
        processed = 0
        
        for char_name, char_scenes in sorted_chars:
            try:
                # Analyze this character
                analysis = analyze_single_character(char_name, char_scenes, scenes)
                
                if analysis:
                    worker_save_character_analysis(script_id, char_name, analysis)
                
                processed += 1
                progress = int(5 + (90 * processed / total_chars))
                worker_update_job_status(job['job_id'], 'processing', progress)
                
            except Exception as e:
                print(f"[Worker] Failed to analyze character {char_name}: {e}")
                continue
        
        worker_update_job_status(job['job_id'], 'completed', 100, f"Analyzed {processed}/{total_chars} characters")
        return True
        
    except Exception as e:
        print(f"[Worker] Characters job failed: {e}")
        worker_update_job_status(job['job_id'], 'failed', error_message=str(e))
        return False


def analyze_single_character(char_name, char_scenes, all_scenes):
    """Analyze a single character, chunking if needed."""
    
    # If character has many scenes, chunk the analysis
    if len(char_scenes) > MAX_SCENES_PER_REQUEST:
        return analyze_character_chunked(char_name, char_scenes, all_scenes)
    
    # Build scene context
    scene_context = "\n".join([
        f"Scene {s['scene_number']} ({s['setting']}): {s['description'][:300]}"
        for s in char_scenes
    ])
    
    prompt = f"""
Analyze this character from a screenplay.

CHARACTER: {char_name}
APPEARS IN {len(char_scenes)} SCENES

SCENE CONTEXT:
{scene_context}

Provide detailed analysis:
1. Description (2-3 sentences)
2. Role type: "Lead", "Supporting", or "Minor"
3. Personality traits (3-5 traits)
4. Backstory (what we can infer)
5. Motivation (what drives them)
6. Character arc summary
7. Scene-by-scene emotional breakdown
8. Relationships with other characters

Return ONLY valid JSON:
{{
    "description": "Character description",
    "role_type": "Lead|Supporting|Minor",
    "traits": ["trait1", "trait2", "trait3"],
    "backstory": "Inferred backstory",
    "motivation": "Character motivation",
    "arc_summary": "Character arc description",
    "scene_breakdown": {{
        "1": {{
            "emotion": "emotion_name",
            "intensity": 1-10,
            "emotional_description": "Description",
            "objective": "Scene objective",
            "key_actions": ["action1", "action2"],
            "dialogue_notes": "Dialogue style",
            "arc_position": "beginning|rising|climax|falling|resolution"
        }}
    }},
    "relationships": [
        {{
            "character": "OTHER_NAME",
            "type": "antagonist|ally|love_interest|family|friend|enemy",
            "description": "Relationship description",
            "dynamic": "Relationship dynamic"
        }}
    ]
}}
"""
    
    return call_gemini(prompt)


def analyze_character_chunked(char_name, char_scenes, all_scenes):
    """Analyze a character with many scenes by chunking."""
    
    # Split scenes into chunks
    chunks = [
        char_scenes[i:i + MAX_SCENES_PER_REQUEST]
        for i in range(0, len(char_scenes), MAX_SCENES_PER_REQUEST)
    ]
    
    all_scene_breakdowns = {}
    
    # Analyze each chunk
    for chunk in chunks:
        scene_context = "\n".join([
            f"Scene {s['scene_number']} ({s['setting']}): {s['description'][:200]}"
            for s in chunk
        ])
        
        prompt = f"""
Analyze {char_name}'s emotional journey in these scenes.

SCENES:
{scene_context}

For each scene, provide:
- Emotional state and intensity (1-10)
- Character's objective
- Key actions
- Dialogue notes
- Arc position

Return ONLY valid JSON:
{{
    "scene_breakdown": {{
        "scene_number": {{
            "emotion": "emotion_name",
            "intensity": 1-10,
            "emotional_description": "Description",
            "objective": "Scene objective",
            "key_actions": ["action1"],
            "dialogue_notes": "Dialogue style",
            "arc_position": "beginning|rising|climax|falling|resolution"
        }}
    }}
}}
"""
        
        try:
            chunk_result = call_gemini(prompt)
            all_scene_breakdowns.update(chunk_result.get('scene_breakdown', {}))
        except Exception as e:
            print(f"[Worker] Chunk analysis failed: {e}")
            continue
    
    # Final synthesis call
    prompt = f"""
Synthesize the character analysis for {char_name} who appears in {len(char_scenes)} scenes.

Based on their journey through the story, provide:
1. Overall description
2. Role type (Lead/Supporting/Minor based on {len(char_scenes)} scenes)
3. Key personality traits
4. Inferred backstory
5. Core motivation
6. Character arc summary
7. Key relationships

Return ONLY valid JSON:
{{
    "description": "Character description",
    "role_type": "Lead|Supporting|Minor",
    "traits": ["trait1", "trait2", "trait3"],
    "backstory": "Inferred backstory",
    "motivation": "Character motivation",
    "arc_summary": "Character arc description",
    "relationships": []
}}
"""
    
    try:
        synthesis = call_gemini(prompt)
        synthesis['scene_breakdown'] = all_scene_breakdowns
        return synthesis
    except Exception as e:
        print(f"[Worker] Synthesis failed: {e}")
        return {
            'description': f"Character appearing in {len(char_scenes)} scenes",
            'role_type': 'Lead' if len(char_scenes) > 10 else 'Supporting',
            'traits': [],
            'scene_breakdown': all_scene_breakdowns
        }


def process_locations_job(job):
    """Process locations analysis."""
    script_id = job['script_id']
    
    try:
        worker_update_job_status(job['job_id'], 'processing', 10)
        
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # Get all scenes grouped by location
        cursor.execute("""
            SELECT setting, scene_number, description 
            FROM scenes WHERE script_id = ? 
            ORDER BY setting, scene_number
        """, (script_id,))
        
        location_scenes = {}
        for row in cursor.fetchall():
            setting = row[0] or 'UNKNOWN'
            if setting not in location_scenes:
                location_scenes[setting] = []
            location_scenes[setting].append({
                'scene_number': row[1],
                'description': row[2]
            })
        
        conn.close()
        
        if not location_scenes:
            worker_update_job_status(job['job_id'], 'failed', error_message="No locations found")
            return False
        
        worker_update_job_status(job['job_id'], 'processing', 30)
        
        # Build location summary
        loc_summary = "\n".join([
            f"- {loc}: {len(scenes)} scene(s)"
            for loc, scenes in location_scenes.items()
        ])
        
        # Sample scene descriptions
        sample_scenes = []
        for loc, scenes in list(location_scenes.items())[:5]:
            for scene in scenes[:2]:
                sample_scenes.append(f"{loc}: {scene['description'][:150]}")
        
        prompt = f"""
Analyze these locations from a screenplay.

LOCATIONS:
{loc_summary}

SAMPLE SCENES:
{chr(10).join(sample_scenes[:10])}

For each location, provide atmosphere and mood analysis.

Return ONLY valid JSON:
{{
    "locations": {{
        "LOCATION_NAME": {{
            "atmosphere": "Mood description",
            "type": "Interior|Exterior",
            "time_of_day": "Day|Night|Various",
            "mood": "tense|calm|romantic|dramatic|etc",
            "production_notes": "Brief production note"
        }}
    }},
    "insights": {{
        "primary_location": "Most used location",
        "location_variety": "low|medium|high"
    }}
}}
"""
        
        result = call_gemini(prompt)
        
        worker_update_job_status(job['job_id'], 'processing', 80)
        
        # Save to existing cache table
        worker_save_locations(script_id, result)
        
        worker_update_job_status(job['job_id'], 'completed', 100, f"Analyzed {len(location_scenes)} locations")
        return True
        
    except Exception as e:
        print(f"[Worker] Locations job failed: {e}")
        worker_update_job_status(job['job_id'], 'failed', error_message=str(e))
        return False


def process_character_detail_job(job):
    """Process a single character analysis on-demand."""
    script_id = job['script_id']
    character_name = job.get('target_id')
    
    if not character_name:
        worker_update_job_status(job['job_id'], 'failed', error_message="No character name specified")
        return False
    
    try:
        worker_update_job_status(job['job_id'], 'processing', 10, f"Analyzing {character_name}...")
        
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # Get all scenes with this character
        cursor.execute("""
            SELECT scene_number, setting, description, characters 
            FROM scenes WHERE script_id = ? 
            ORDER BY scene_number
        """, (script_id,))
        
        all_scenes = []
        char_scenes = []
        
        for row in cursor.fetchall():
            scene = {
                'scene_number': row[0],
                'setting': row[1],
                'description': row[2],
                'characters': json.loads(row[3]) if row[3] else []
            }
            all_scenes.append(scene)
            
            # Check if character is in this scene (case-insensitive)
            if any(c.upper() == character_name.upper() for c in scene['characters']):
                char_scenes.append(scene)
        
        conn.close()
        
        if not char_scenes:
            worker_update_job_status(job['job_id'], 'failed', error_message=f"Character '{character_name}' not found in any scenes")
            return False
        
        worker_update_job_status(job['job_id'], 'processing', 30, f"Found {len(char_scenes)} scenes...")
        
        # Analyze the character
        analysis = analyze_single_character(character_name, char_scenes, all_scenes)
        
        worker_update_job_status(job['job_id'], 'processing', 80, "Saving analysis...")
        
        if analysis:
            worker_save_character_analysis(script_id, character_name, analysis)
        
        worker_update_job_status(job['job_id'], 'completed', 100, f"Analyzed {character_name} ({len(char_scenes)} scenes)")
        return True
        
    except Exception as e:
        print(f"[Worker] Character detail job failed: {e}")
        worker_update_job_status(job['job_id'], 'failed', error_message=str(e))
        return False


def process_location_detail_job(job):
    """Process a single location analysis on-demand."""
    script_id = job['script_id']
    location_name = job.get('target_id')
    
    if not location_name:
        worker_update_job_status(job['job_id'], 'failed', error_message="No location name specified")
        return False
    
    try:
        worker_update_job_status(job['job_id'], 'processing', 10, f"Analyzing {location_name}...")
        
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # Get all scenes at this location
        cursor.execute("""
            SELECT scene_number, setting, description, characters
            FROM scenes WHERE script_id = ? AND UPPER(setting) = UPPER(?)
            ORDER BY scene_number
        """, (script_id, location_name))
        
        location_scenes = []
        for row in cursor.fetchall():
            location_scenes.append({
                'scene_number': row[0],
                'setting': row[1],
                'description': row[2],
                'characters': json.loads(row[3]) if row[3] else []
            })
        
        conn.close()
        
        if not location_scenes:
            worker_update_job_status(job['job_id'], 'failed', error_message=f"Location '{location_name}' not found")
            return False
        
        worker_update_job_status(job['job_id'], 'processing', 30, f"Found {len(location_scenes)} scenes...")
        
        # Build scene context
        scene_context = "\n".join([
            f"Scene {s['scene_number']}: {s['description'][:200]} (Characters: {', '.join(s['characters'][:5])})"
            for s in location_scenes[:10]
        ])
        
        prompt = f"""
Analyze this location from a screenplay.

LOCATION: {location_name}
APPEARS IN {len(location_scenes)} SCENES

SCENE CONTEXT:
{scene_context}

Provide detailed analysis:
1. Description of the location
2. Atmosphere and mood
3. Significance to the story
4. Key events that happen here
5. Characters commonly seen here

Return ONLY valid JSON:
{{
    "description": "Location description",
    "atmosphere": "Mood and atmosphere",
    "significance": "Story significance",
    "key_events": ["event1", "event2"],
    "common_characters": ["char1", "char2"],
    "scene_count": {len(location_scenes)}
}}
"""
        
        worker_update_job_status(job['job_id'], 'processing', 50, "Calling AI...")
        
        result = call_gemini(prompt)
        
        worker_update_job_status(job['job_id'], 'processing', 80, "Saving analysis...")
        
        # Save to location_analysis table
        worker_save_location_analysis(script_id, location_name, result)
        
        worker_update_job_status(job['job_id'], 'completed', 100, f"Analyzed {location_name} ({len(location_scenes)} scenes)")
        return True
        
    except Exception as e:
        print(f"[Worker] Location detail job failed: {e}")
        worker_update_job_status(job['job_id'], 'failed', error_message=str(e))
        return False


def worker_save_location_analysis(script_id, location_name, analysis):
    """Save single location analysis to database."""
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO location_analysis 
            (script_id, location_name, analysis_data, created_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (script_id, location_name, json.dumps(analysis)))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Worker] Failed to save location analysis: {e}")


# ============================================
# Helper Functions
# ============================================

def get_act_samples(scenes):
    """Get representative scenes from each act for story arc analysis."""
    total = len(scenes)
    
    if total <= 9:
        return scenes
    
    # 3-act structure sampling
    act1_end = int(total * 0.25)
    act2_end = int(total * 0.75)
    
    samples = []
    
    # Act 1: First, middle, last
    samples.append(scenes[0])
    samples.append(scenes[act1_end // 2])
    samples.append(scenes[max(0, act1_end - 1)])
    
    # Act 2: First, midpoint, last
    samples.append(scenes[act1_end])
    samples.append(scenes[(act1_end + act2_end) // 2])
    samples.append(scenes[max(0, act2_end - 1)])
    
    # Act 3: First, climax, final
    samples.append(scenes[act2_end])
    samples.append(scenes[(act2_end + total) // 2])
    samples.append(scenes[-1])
    
    return samples


# ============================================
# Worker Control
# ============================================

def process_scene_enhancement_job(job):
    """
    Process scene enhancement using the new v2 pipeline.
    
    This job:
    1. Gets all pending scene candidates
    2. Enhances each with AI (characters, props, etc.)
    3. Saves to scenes table
    """
    script_id = job['script_id']
    
    try:
        worker_update_job_status(job['job_id'], 'processing', 5, "Starting scene enhancement...")
        
        from services.scene_enhancer import process_all_candidates
        
        conn = get_worker_db()
        
        def progress_callback(current, total, scene_num):
            progress = int(5 + (90 * current / total))
            worker_update_job_status(
                job['job_id'], 
                'processing', 
                progress, 
                f"Scene {scene_num} ({current}/{total})"
            )
        
        result = process_all_candidates(script_id, conn, progress_callback)
        conn.close()
        
        processed = result.get('processed', 0)
        failed = result.get('failed', 0)
        total = result.get('total', 0)
        
        if failed > 0 and processed == 0:
            worker_update_job_status(
                job['job_id'], 
                'failed', 
                error_message=f"All {failed} scenes failed to process"
            )
            return False
        
        summary = f"Enhanced {processed}/{total} scenes"
        if failed > 0:
            summary += f" ({failed} failed)"
        
        worker_update_job_status(job['job_id'], 'completed', 100, summary)
        return True
        
    except Exception as e:
        print(f"[Worker] Scene enhancement job failed: {e}")
        worker_update_job_status(job['job_id'], 'failed', error_message=str(e))
        return False


def process_job(job):
    """Process a single job based on its type."""
    job_type = job['job_type']
    
    processors = {
        'scene_extraction': process_scene_extraction_job,
        'scene_enhancement': process_scene_enhancement_job,  # New v2 pipeline
        'overview': process_overview_job,
        'story_arc': process_story_arc_job,
        'characters': process_characters_job,
        'character_detail': process_character_detail_job,  # Single character on-demand
        'locations': process_locations_job,
        'location_detail': process_location_detail_job,  # Single location on-demand
    }
    
    processor = processors.get(job_type)
    if not processor:
        worker_update_job_status(job['job_id'], 'failed', error_message=f"Unknown job type: {job_type}")
        return False
    
    return processor(job)


def recover_stale_jobs():
    """
    Recover jobs stuck in 'processing' state (from server crash/restart).
    Reset them to 'queued' so they can be re-processed.
    """
    try:
        conn = get_worker_db()
        cursor = conn.cursor()
        
        # Find jobs that have been processing for more than 10 minutes
        cursor.execute("""
            UPDATE analysis_jobs 
            SET status = 'queued', 
                started_at = NULL,
                error_message = 'Recovered from stale processing state'
            WHERE status = 'processing' 
            AND started_at < datetime('now', '-10 minutes')
        """)
        
        recovered = cursor.rowcount
        
        if recovered > 0:
            print(f"[Worker] Recovered {recovered} stale jobs")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"[Worker] Error recovering stale jobs: {e}")


def worker_loop():
    """Main worker loop - polls queue and processes jobs."""
    global _worker_running
    
    print("[Worker] Starting analysis worker...")
    
    # Recover any stale jobs from previous runs
    recover_stale_jobs()
    
    while _worker_running:
        try:
            job = worker_get_next_job()
            
            if job:
                print(f"[Worker] Processing job {job['job_id']}: {job['job_type']}")
                
                # Update script status
                worker_update_script_status(job['script_id'], 'in_progress')
                
                success = process_job(job)
                
                if not success and job['retry_count'] < job['max_retries']:
                    print(f"[Worker] Retrying job {job['job_id']}")
                    worker_retry_job(job['job_id'])
                
                # Check if all jobs for this script are done
                worker_check_script_completion(job['script_id'])
            else:
                # No jobs, wait before polling again
                time.sleep(WORKER_POLL_INTERVAL)
                
        except Exception as e:
            print(f"[Worker] Error in worker loop: {e}")
            time.sleep(WORKER_POLL_INTERVAL)
    
    print("[Worker] Worker stopped.")


def start_worker():
    """Start the background worker thread."""
    global _worker_running, _worker_thread
    
    if _worker_running:
        print("[Worker] Worker already running")
        return
    
    _worker_running = True
    _worker_thread = threading.Thread(target=worker_loop, daemon=True)
    _worker_thread.start()
    print("[Worker] Worker thread started")


def stop_worker():
    """Stop the background worker."""
    global _worker_running
    _worker_running = False
    print("[Worker] Stopping worker...")


# Auto-start worker when module is imported
# Uncomment the line below to enable auto-start
# start_worker()
