"""
LangExtract Service for Screenplay Extraction
Integrates LangExtract with Supabase for structured screenplay analysis.
"""

import os
import json
import time
from typing import List, Dict, Optional, Generator, Callable
from datetime import datetime
import langextract as lx
from .langextract_schema import SCREENPLAY_EXTRACTION_SCHEMA, SCREENPLAY_EXTRACTION_PROMPT
from .langextract_examples import get_examples
from config.langextract_config import get_config


def _extract_with_direct_gemini(text, api_key, model, successful_extractions, errors, progress_callback=None):
    """
    Extract screenplay elements using direct Gemini API calls with chunking.
    Used as primary path for large scripts (>50K chars) and as fallback for smaller scripts.
    """
    import requests as req_lib
    import re as re_lib
    
    if progress_callback:
        progress_callback(5, "Starting direct Gemini extraction")
    
    # Use v1beta for gemini-2.5-flash, v1 for older models
    model_id = model or 'gemini-2.5-flash'
    if '2.5' in model_id or '2.0' in model_id:
        api_base = 'https://generativelanguage.googleapis.com/v1beta'
    else:
        api_base = 'https://generativelanguage.googleapis.com/v1'
    api_url = f'{api_base}/models/{model_id}:generateContent'
    req_headers = {'Content-Type': 'application/json'}
    
    print(f"[LangExtract Direct] Using model: {model_id}, API: {api_base}")
    
    # Split at scene boundaries (INT./EXT. headers) so no scene is split across chunks
    # Target ~8K chars per chunk but always break at scene headers
    TARGET_CHUNK = 8000
    MAX_CHUNK = 12000
    
    # Find all scene header positions
    scene_starts = [m.start() for m in re_lib.finditer(
        r'(?m)^[ \t]*(?:INT\.|EXT\.|INT\./EXT\.|INT/EXT|I/E)', text
    )]
    
    chunks = []
    chunk_start = 0
    
    if scene_starts:
        for i, pos in enumerate(scene_starts):
            chunk_len = pos - chunk_start
            # Start a new chunk at this scene header if we've exceeded target size
            if chunk_len >= TARGET_CHUNK and pos > chunk_start:
                chunks.append((chunk_start, text[chunk_start:pos]))
                chunk_start = pos
        # Add final chunk
        if chunk_start < len(text):
            chunks.append((chunk_start, text[chunk_start:]))
    
    # Fallback: if no scene headers found or chunks are too large, use fixed splitting
    if not chunks:
        for i in range(0, len(text), TARGET_CHUNK):
            chunks.append((i, text[i:i + TARGET_CHUNK]))
    else:
        # Split any oversized chunks (>MAX_CHUNK) that contain many scenes
        final_chunks = []
        for offset, chunk_text in chunks:
            if len(chunk_text) > MAX_CHUNK:
                for j in range(0, len(chunk_text), TARGET_CHUNK):
                    final_chunks.append((offset + j, chunk_text[j:j + TARGET_CHUNK]))
            else:
                final_chunks.append((offset, chunk_text))
        chunks = final_chunks
    
    print(f"[LangExtract Direct] Processing {len(chunks)} scene-aligned chunks (target ~{TARGET_CHUNK} chars)")
    
    for chunk_idx, (offset, chunk_text) in enumerate(chunks):
        try:
            if progress_callback:
                pct = 5 + int(90 * (chunk_idx / max(len(chunks), 1)))
                progress_callback(pct, f"Processing chunk {chunk_idx + 1}/{len(chunks)}")
            
            prompt = f"""You are a professional screenplay breakdown assistant. Your task is to extract EVERY notable element from this screenplay text. Be thorough — do not skip any element.

Return ONLY a valid JSON array. Each object must have exactly these fields:
- "class": MUST be one of: character, location_detail, prop, dialogue, wardrobe, makeup_hair, vehicle, sound, special_fx, action, emotion, transition, scene_header, relationship
- "text": the exact text from the screenplay

EXTRACTION RULES:
1. **scene_header**: Every "INT." or "EXT." line (e.g. "INT. KITCHEN - NIGHT")
2. **character**: Every character name that appears in ALL CAPS before dialogue or in action lines
3. **prop**: Physical objects characters interact with (guns, phones, letters, food, furniture, etc.)
4. **wardrobe**: Clothing, uniforms, costumes, accessories worn by characters
5. **makeup_hair**: Hairstyles, makeup, scars, wounds, blood, physical appearance changes
6. **vehicle**: Cars, trucks, bikes, boats, aircraft — any transport
7. **sound**: Sound effects, music cues, ambient sounds mentioned in action lines
8. **special_fx**: Rain, fire, explosions, CGI effects, stunts, weather effects
9. **location_detail**: Specific details about settings (dirty walls, broken window, etc.)
10. **dialogue**: Important or notable lines of dialogue
11. **action**: Key action beats and stage directions
12. **emotion**: Character emotional states explicitly described
13. **transition**: CUT TO, FADE IN, DISSOLVE TO, etc.

Be EXHAUSTIVE. Extract every character name, every prop, every wardrobe item. Do not summarize — extract the actual text.

SCREENPLAY TEXT:
{chunk_text}

Return ONLY the JSON array, nothing else."""
            
            payload = {
                'contents': [{'parts': [{'text': prompt}]}],
                'generationConfig': {
                    'temperature': 0.1,
                    'maxOutputTokens': 16384
                },
                'safetySettings': [
                    {'category': 'HARM_CATEGORY_HARASSMENT', 'threshold': 'BLOCK_NONE'},
                    {'category': 'HARM_CATEGORY_HATE_SPEECH', 'threshold': 'BLOCK_NONE'},
                    {'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'threshold': 'BLOCK_NONE'},
                    {'category': 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold': 'BLOCK_NONE'},
                ]
            }
            
            resp = req_lib.post(
                f'{api_url}?key={api_key}',
                headers=req_headers,
                json=payload,
                timeout=(10, 120)  # 10s connect, 120s read
            )
            resp.raise_for_status()
            
            resp_json = resp.json()
            
            # Debug: log response structure for first chunk
            if chunk_idx == 0:
                candidates = resp_json.get('candidates', [])
                print(f"[LangExtract Direct] Response keys: {list(resp_json.keys())}")
                if candidates:
                    c0 = candidates[0]
                    finish_reason = c0.get('finishReason', 'unknown')
                    print(f"[LangExtract Direct] finishReason: {finish_reason}")
                    if 'content' in c0:
                        parts = c0['content'].get('parts', [])
                        print(f"[LangExtract Direct] parts count: {len(parts)}")
                        if parts:
                            text_preview = parts[0].get('text', '')[:200]
                            print(f"[LangExtract Direct] Response preview: {text_preview}")
                    else:
                        print(f"[LangExtract Direct] No 'content' in candidate. Keys: {list(c0.keys())}")
                        # Check for safety block
                        if 'safetyRatings' in c0:
                            print(f"[LangExtract Direct] Safety ratings: {c0['safetyRatings']}")
                else:
                    print(f"[LangExtract Direct] No candidates in response!")
                    if 'promptFeedback' in resp_json:
                        print(f"[LangExtract Direct] Prompt feedback: {resp_json['promptFeedback']}")
            
            # Safely extract response text
            candidates = resp_json.get('candidates', [])
            if not candidates:
                feedback = resp_json.get('promptFeedback', {})
                block_reason = feedback.get('blockReason', 'unknown')
                print(f"[LangExtract Direct] Chunk {chunk_idx + 1} blocked: {block_reason}")
                errors.append({'type': 'blocked', 'chunk': chunk_idx, 'reason': block_reason})
                continue
            
            candidate = candidates[0]
            finish_reason = candidate.get('finishReason', '')
            
            if 'content' not in candidate or 'parts' not in candidate.get('content', {}):
                print(f"[LangExtract Direct] Chunk {chunk_idx + 1} no content (finishReason={finish_reason})")
                errors.append({'type': 'no_content', 'chunk': chunk_idx, 'finishReason': finish_reason})
                continue
            
            parts = candidate['content']['parts']
            if not parts or 'text' not in parts[0]:
                print(f"[LangExtract Direct] Chunk {chunk_idx + 1} empty parts")
                errors.append({'type': 'empty_parts', 'chunk': chunk_idx})
                continue
            
            resp_text = parts[0]['text'].strip()
            
            if not resp_text:
                print(f"[LangExtract Direct] Chunk {chunk_idx + 1} empty response text")
                errors.append({'type': 'empty_text', 'chunk': chunk_idx})
                continue
            
            # Strip markdown code fences
            resp_text = re_lib.sub(r'^```(?:json)?\s*', '', resp_text)
            resp_text = re_lib.sub(r'\s*```\s*$', '', resp_text)
            resp_text = resp_text.strip()
            
            # Handle truncated JSON (finishReason: MAX_TOKENS)
            if finish_reason == 'MAX_TOKENS' and resp_text.startswith('[') and not resp_text.rstrip().endswith(']'):
                # Find last complete JSON object (ends with })
                last_brace = resp_text.rfind('}')
                if last_brace > 0:
                    resp_text = resp_text[:last_brace + 1] + ']'
                    print(f"[LangExtract Direct] Chunk {chunk_idx + 1} truncated — repaired JSON")
            
            chunk_extractions = json.loads(resp_text)
            
            chunk_count = 0
            for item in chunk_extractions:
                if isinstance(item, dict) and 'class' in item and 'text' in item:
                    ext_text = item.get('text', '')
                    # Find actual position in chunk text for accurate scene linking
                    local_start = chunk_text.find(ext_text)
                    if local_start >= 0:
                        text_start = offset + local_start
                        text_end = text_start + len(ext_text)
                    else:
                        # Fallback: use Gemini's positions or chunk offset
                        text_start = offset + item.get('start', 0)
                        text_end = offset + item.get('end', len(ext_text))
                    
                    successful_extractions.append({
                        'extraction_class': item.get('class', 'unknown'),
                        'extraction_text': ext_text,
                        'text_start': text_start,
                        'text_end': text_end,
                        'confidence': 0.85 if local_start >= 0 else 0.6,
                        'attributes': {}
                    })
                    chunk_count += 1
            
            print(f"[LangExtract Direct] Chunk {chunk_idx + 1}/{len(chunks)}: {chunk_count} extractions")
            
            # Rate limit between chunks to avoid hitting Gemini quotas
            if chunk_idx < len(chunks) - 1:
                time.sleep(1.5)
            
        except json.JSONDecodeError as json_err:
            print(f"[LangExtract Direct] Chunk {chunk_idx + 1} JSON parse error: {json_err}")
            # Log the actual text that failed to parse
            if 'resp_text' in dir():
                print(f"[LangExtract Direct] Failed text (first 300 chars): {repr(resp_text[:300])}")
            errors.append({'type': 'direct_parse_error', 'chunk': chunk_idx, 'message': str(json_err)})
        except req_lib.exceptions.Timeout:
            print(f"[LangExtract Direct] Chunk {chunk_idx + 1} timed out (180s)")
            errors.append({'type': 'direct_timeout', 'chunk': chunk_idx})
        except Exception as chunk_err:
            print(f"[LangExtract Direct] Chunk {chunk_idx + 1} error: {str(chunk_err)}")
            errors.append({'type': 'direct_chunk_error', 'chunk': chunk_idx, 'message': str(chunk_err)})
            # If we get a rate limit error, wait longer
            if '429' in str(chunk_err) or 'quota' in str(chunk_err).lower():
                print(f"[LangExtract Direct] Rate limited, waiting 10s...")
                time.sleep(10)
    
    print(f"[LangExtract Direct] Total: {len(successful_extractions)} extractions from {len(chunks)} chunks")
    
    if progress_callback:
        progress_callback(100, "Extraction complete")


def extract_with_langextract(
    text: str,
    model: str = None,
    max_workers: int = None,
    chunk_size: int = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    max_retries: int = None
) -> Dict:
    """
    Extract screenplay elements using LangExtract with Gemini.
    Enhanced with progress tracking, error recovery, and retry logic.
    
    Args:
        text: Full script text
        model: Gemini model to use (default from config)
        max_workers: Number of parallel workers (default from config)
        chunk_size: Characters per chunk (default from config)
        progress_callback: Optional callback(percentage, current_class) for progress updates
        max_retries: Maximum retry attempts for failed chunks (default from config)
        
    Returns:
        Dictionary with:
            - extractions: List of extraction dictionaries
            - stats: Extraction statistics
            - errors: List of errors encountered
        
    Raises:
        ValueError: If GOOGLE_API_KEY not found
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    
    # Load configuration
    config = get_config()
    model = model or config.model
    max_workers = max_workers or config.max_workers
    chunk_size = chunk_size or config.chunk_size
    max_retries = max_retries if max_retries is not None else config.max_retries
    
    print(f"[LangExtract] Initializing with model: {model}")
    print(f"[LangExtract] Config: chunk_size={chunk_size}, max_workers={max_workers}, max_retries={max_retries}")
    
    start_time = time.time()
    errors = []
    successful_extractions = []
    
    # Get examples for few-shot learning
    examples = get_examples()
    
    print(f"[LangExtract] Using model: {model}")
    print(f"[LangExtract] Examples: {len(examples)} few-shot examples")
    print(f"[LangExtract] Text length: {len(text)} characters")
    
    # Sanitize text — remove null bytes, BOM, and control chars that break LangExtract
    import re
    original_len = len(text)
    text = text.replace('\x00', '')           # Null bytes
    text = text.replace('\ufeff', '')          # BOM
    text = text.replace('\ufffe', '')          # Reverse BOM
    text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)  # Control chars (keep \t \n \r)
    text = re.sub(r'\r\n', '\n', text)         # Normalize line endings
    text = re.sub(r'\r', '\n', text)
    if len(text) != original_len:
        print(f"[LangExtract] Sanitized text: {original_len} -> {len(text)} chars ({original_len - len(text)} removed)")
    
    if not text or not text.strip():
        raise ValueError("Script text is empty after sanitization")
    
    text_len = len(text)
    
    # For large scripts (>50K), skip lx.extract() entirely — it fails with
    # "Empty or invalid input string" and wastes ~3 minutes. Use direct Gemini API instead.
    use_direct_api = text_len > 50000
    
    if use_direct_api:
        print(f"[LangExtract] Large script ({text_len} chars) — using direct Gemini API (skipping lx.extract)")
        _extract_with_direct_gemini(text, api_key, model, successful_extractions, errors, progress_callback)
    else:
        # For smaller scripts, try lx.extract() first with fallback
        if text_len > 20000:
            chunk_size = max(chunk_size, 5000)
            max_workers = min(max_workers, 5)
            print(f"[LangExtract] Medium script ({text_len} chars) — adjusted: chunk_size={chunk_size}, max_workers={max_workers}")
        
        try:
            if progress_callback:
                progress_callback(5, "Initializing extraction")
            
            result = lx.extract(
                text_or_documents=text,
                prompt_description=SCREENPLAY_EXTRACTION_PROMPT,
                examples=examples,
                model_id=model,
                extraction_passes=2,
                max_workers=max_workers,
                max_char_buffer=chunk_size,
                api_key=api_key
            )
            
            if progress_callback:
                progress_callback(90, "Processing results")
            
            if hasattr(result, 'extractions'):
                extractions_list = result.extractions
            elif isinstance(result, list):
                extractions_list = result
            else:
                extractions_list = []
            
            print(f"[LangExtract] Extracted {len(extractions_list)} elements")
            
            for extraction in extractions_list:
                try:
                    extraction_dict = {
                        'extraction_class': extraction.extraction_class,
                        'extraction_text': extraction.extraction_text,
                        'text_start': extraction.char_interval.start_pos if extraction.char_interval else 0,
                        'text_end': extraction.char_interval.end_pos if extraction.char_interval else len(extraction.extraction_text),
                        'attributes': extraction.attributes if extraction.attributes else {},
                        'confidence': getattr(extraction, 'confidence', 1.0)
                    }
                    successful_extractions.append(extraction_dict)
                except Exception as e:
                    error_msg = f"Failed to process extraction: {str(e)}"
                    print(f"[LangExtract] {error_msg}")
                    errors.append({
                        'type': 'processing_error',
                        'message': error_msg,
                        'timestamp': datetime.utcnow().isoformat()
                    })
            
            if progress_callback:
                progress_callback(100, "Extraction complete")
            
        except Exception as e:
            error_msg = f"lx.extract() failed: {str(e)}"
            print(f"[LangExtract] {error_msg}")
            print(f"[LangExtract] Falling back to direct Gemini API extraction")
            
            _extract_with_direct_gemini(text, api_key, model, successful_extractions, errors, progress_callback)
    
    elapsed_time = time.time() - start_time
    
    stats = {
        'total_extractions': len(successful_extractions),
        'total_errors': len(errors),
        'elapsed_time': round(elapsed_time, 2),
        'text_length': len(text),
        'success_rate': len(successful_extractions) / max(len(successful_extractions) + len(errors), 1)
    }
    
    print(f"[LangExtract] Stats: {stats}")
    
    return {
        'extractions': successful_extractions,
        'stats': stats,
        'errors': errors
    }


# Note: Retry logic is now handled internally by langextract.extract()
# The functional API manages retries and error handling automatically


def save_extractions_to_supabase(
    script_id: str,
    extractions: List[Dict],
    supabase_client,
    link_to_scenes: bool = True
) -> int:
    """
    Save LangExtract results to Supabase extraction_metadata table.
    Enhanced with automatic scene_id linking based on text positions.
    
    Args:
        script_id: UUID of the script
        extractions: List of extraction dictionaries
        supabase_client: Supabase client instance
        link_to_scenes: If True, automatically link extractions to scenes
        
    Returns:
        Number of extractions saved
    """
    if not extractions:
        print("[LangExtract] No extractions to save")
        return 0
    
    print(f"[LangExtract] Saving {len(extractions)} extractions to Supabase")
    
    # Get scene boundaries for linking if requested
    scene_boundaries = []
    if link_to_scenes:
        try:
            scenes = supabase_client.table('scenes')\
                .select('id, text_start, text_end')\
                .eq('script_id', script_id)\
                .order('text_start')\
                .execute()
            
            if scenes.data:
                scene_boundaries = scenes.data
                print(f"[LangExtract] Loaded {len(scene_boundaries)} scene boundaries for linking")
        except Exception as e:
            print(f"[LangExtract] Warning: Could not load scene boundaries: {str(e)}")
    
    # Prepare data for batch insert with scene linking
    records = []
    linked_count = 0
    
    # Valid extraction classes per DB constraint
    VALID_CLASSES = {
        'scene_header', 'character', 'prop', 'wardrobe', 'dialogue', 'action',
        'emotion', 'relationship', 'special_fx', 'vehicle', 'sound',
        'location_detail', 'transition', 'makeup_hair'
    }
    # Map common Gemini outputs to valid classes
    CLASS_MAP = {
        'camera_direction': 'action',
        'color': 'prop',
        'sfx': 'special_fx',
        'vfx': 'special_fx',
        'location': 'location_detail',
        'costume': 'wardrobe',
        'hair': 'makeup_hair',
        'makeup': 'makeup_hair',
    }
    
    skipped = 0
    # Track character names per scene for dedup (key: (scene_id, normalized_name))
    seen_characters = set()
    deduped = 0
    
    for extraction in extractions:
        # Map/validate extraction class
        ext_class = extraction['extraction_class']
        if ext_class not in VALID_CLASSES:
            ext_class = CLASS_MAP.get(ext_class)
            if not ext_class:
                skipped += 1
                continue
        
        ext_text = extraction['extraction_text']
        
        # Normalize character names to UPPER CASE (screenplay convention)
        if ext_class == 'character':
            ext_text = ext_text.strip().upper()
        
        # Find matching scene based on text_start position
        scene_id = None
        if scene_boundaries:
            scene_id = _find_scene_for_extraction(extraction['text_start'], scene_boundaries)
            if scene_id:
                linked_count += 1
        
        # Deduplicate characters: same name + same scene = keep first only
        if ext_class == 'character':
            dedup_key = (scene_id, ext_text)
            if dedup_key in seen_characters:
                deduped += 1
                continue
            seen_characters.add(dedup_key)
        
        record = {
            'script_id': script_id,
            'scene_id': scene_id,
            'extraction_class': ext_class,
            'extraction_text': ext_text,
            'text_start': extraction['text_start'],
            'text_end': extraction['text_end'],
            'attributes': extraction.get('attributes', {}),
            'confidence': extraction.get('confidence', 1.0)
        }
        records.append(record)
    
    if skipped:
        print(f"[LangExtract] Skipped {skipped} extractions with unmapped classes")
    if deduped:
        print(f"[LangExtract] Deduped {deduped} duplicate character entries")
    
    try:
        # Batch insert to Supabase
        response = supabase_client.table('extraction_metadata').insert(records).execute()
        
        saved_count = len(response.data) if response.data else 0
        print(f"[LangExtract] Saved {saved_count} extractions ({linked_count} linked to scenes)")
        
        return saved_count
        
    except Exception as e:
        print(f"[LangExtract] Failed to save extractions: {str(e)}")
        raise


def _find_scene_for_extraction(text_start: int, scene_boundaries: List[Dict]) -> Optional[str]:
    """
    Find the scene_id for an extraction based on its text_start position.
    
    Args:
        text_start: Start position of the extraction
        scene_boundaries: List of scene dictionaries with id, text_start, text_end
        
    Returns:
        Scene ID if found, None otherwise
    """
    for scene in scene_boundaries:
        scene_start = scene.get('text_start', 0)
        scene_end = scene.get('text_end')
        
        # Check if extraction falls within scene boundaries
        if scene_end is None:
            # Last scene - check if extraction is after scene start
            if text_start >= scene_start:
                return scene['id']
        else:
            # Check if extraction is within scene range
            if scene_start <= text_start < scene_end:
                return scene['id']
    
    return None


def generate_visualization(
    script_id: str,
    script_text: str,
    extractions: List[Dict],
    supabase_client
) -> str:
    """
    Generate HTML visualization from LangExtract results.
    
    Args:
        script_id: UUID of the script
        script_text: Full script text
        extractions: List of extraction dictionaries
        supabase_client: Supabase client instance
        
    Returns:
        HTML content as string
    """
    print(f"[LangExtract] Generating visualization for script {script_id}")
    
    try:
        # Convert extractions to LangExtract format
        lx_extractions = []
        for ext in extractions:
            lx_ext = lx.data.Extraction(
                extraction_class=ext['extraction_class'],
                extraction_text=ext['extraction_text'],
                text_start=ext['text_start'],
                text_end=ext['text_end'],
                attributes=ext.get('attributes', {})
            )
            lx_extractions.append(lx_ext)
        
        # Generate HTML using LangExtract's built-in visualization
        from langextract.visualization import create_html_visualization
        
        html_content = create_html_visualization(
            text=script_text,
            extractions=lx_extractions,
            title=f"Script Breakdown - {script_id}"
        )
        
        file_size = len(html_content)
        print(f"[LangExtract] Generated visualization: {file_size} bytes")
        
        # Save to Supabase
        viz_record = {
            'script_id': script_id,
            'html_content': html_content,
            'file_size': file_size
        }
        
        supabase_client.table('extraction_visualizations').insert(viz_record).execute()
        
        # Update script flag
        supabase_client.table('scripts').update({
            'has_visualization': True
        }).eq('id', script_id).execute()
        
        print(f"[LangExtract] Visualization saved to database")
        
        return html_content
        
    except Exception as e:
        print(f"[LangExtract] Visualization generation failed: {str(e)}")
        raise


def get_extractions_by_class(
    script_id: str,
    extraction_class: str,
    supabase_client
) -> List[Dict]:
    """
    Get all extractions of a specific class for a script.
    
    Args:
        script_id: UUID of the script
        extraction_class: Class name (e.g., 'dialogue', 'prop')
        supabase_client: Supabase client instance
        
    Returns:
        List of extraction dictionaries
    """
    try:
        response = supabase_client.table('extraction_metadata')\
            .select('*')\
            .eq('script_id', script_id)\
            .eq('extraction_class', extraction_class)\
            .order('text_start')\
            .execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        print(f"[LangExtract] Failed to get extractions: {str(e)}")
        raise


def get_extraction_stats(script_id: str, supabase_client) -> Dict:
    """
    Get extraction statistics for a script.
    
    Args:
        script_id: UUID of the script
        supabase_client: Supabase client instance
        
    Returns:
        Dictionary with stats per extraction class
    """
    try:
        # Get all extractions for the script
        response = supabase_client.table('extraction_metadata')\
            .select('extraction_class, confidence')\
            .eq('script_id', script_id)\
            .execute()
        
        if not response.data:
            return {}
        
        # Calculate stats per class
        stats = {}
        for row in response.data:
            class_name = row['extraction_class']
            confidence = row.get('confidence', 1.0)
            
            if class_name not in stats:
                stats[class_name] = {
                    'count': 0,
                    'total_confidence': 0.0
                }
            
            stats[class_name]['count'] += 1
            stats[class_name]['total_confidence'] += confidence
        
        # Calculate averages
        for class_name in stats:
            count = stats[class_name]['count']
            total = stats[class_name]['total_confidence']
            stats[class_name]['avg_confidence'] = round(total / count, 2) if count > 0 else 0.0
            del stats[class_name]['total_confidence']
        
        return stats
        
    except Exception as e:
        print(f"[LangExtract] Failed to get stats: {str(e)}")
        raise


def get_visualization(script_id: str, supabase_client) -> Optional[str]:
    """
    Get HTML visualization for a script.
    
    Args:
        script_id: UUID of the script
        supabase_client: Supabase client instance
        
    Returns:
        HTML content string or None if not found
    """
    try:
        response = supabase_client.table('extraction_visualizations')\
            .select('html_content')\
            .eq('script_id', script_id)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]['html_content']
        
        return None
        
    except Exception as e:
        print(f"[LangExtract] Failed to get visualization: {str(e)}")
        raise


def save_performance_metrics(
    script_id: str,
    job_id: str,
    metrics: Dict,
    supabase_client
) -> bool:
    """
    Save performance metrics to extraction_metadata table or analysis_jobs.
    
    Args:
        script_id: UUID of the script
        job_id: Analysis job ID
        metrics: Dictionary with performance metrics
        supabase_client: Supabase client instance
        
    Returns:
        True if saved successfully
    """
    try:
        # Store metrics in analysis_jobs result_data
        from db.supabase_client import SupabaseDB
        db = SupabaseDB()
        
        # Get current job data
        job = supabase_client.table('analysis_jobs')\
            .select('result_data')\
            .eq('id', job_id)\
            .single()\
            .execute()
        
        if job.data:
            result_data = job.data.get('result_data', {})
            result_data['performance_metrics'] = metrics
            
            db.update_job_status(
                job_id,
                job.data.get('status', 'completed'),
                result_data=result_data
            )
            
            print(f"[LangExtract] Performance metrics saved: {metrics}")
            return True
        
        return False
        
    except Exception as e:
        print(f"[LangExtract] Failed to save performance metrics: {str(e)}")
        return False


# DEPRECATED: aggregate_extractions_to_scenes() was removed in the SSoT refactor.
# All consumers now read directly from extraction_metadata via:
#   - GET /api/scripts/:id/scenes/:sceneId/breakdown (frontend)
#   - ReportService._enrich_with_extraction_metadata() (reports)
#   - ExtractionStats useMemo (frontend stats)
# See docs/rich_update.md for migration details.
