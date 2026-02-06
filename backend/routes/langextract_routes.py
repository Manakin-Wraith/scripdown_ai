"""
LangExtract API Routes
Endpoints for accessing extraction data and visualizations.
"""

from flask import Blueprint, jsonify, request, Response, stream_with_context
import json
import time
import os
import threading
from datetime import datetime
from services.langextract_service import (
    get_extractions_by_class,
    get_extraction_stats,
    get_visualization,
    extract_with_langextract,
    save_extractions_to_supabase
)
from db.supabase_client import get_supabase_client, get_supabase_admin, SupabaseDB

langextract_bp = Blueprint('langextract', __name__)

# Global dictionary to track active extractions for cancellation
_active_extractions = {}


@langextract_bp.route('/api/scripts/<script_id>/extractions', methods=['GET'])
def get_script_extractions(script_id):
    """
    Get all extractions for a script, optionally filtered by class.
    
    Query params:
        class: Optional extraction class filter (e.g., 'dialogue', 'prop')
    
    Returns:
        JSON with extractions array
    """
    try:
        # Use admin client to bypass RLS (script ownership already verified by route access)
        supabase = get_supabase_admin()
        extraction_class = request.args.get('class')
        
        if extraction_class:
            # Get specific class
            extractions = get_extractions_by_class(script_id, extraction_class, supabase)
        else:
            # Get all extractions
            response = supabase.table('extraction_metadata')\
                .select('*')\
                .eq('script_id', script_id)\
                .order('text_start')\
                .execute()
            
            extractions = response.data if response.data else []
        
        return jsonify({
            'script_id': script_id,
            'extraction_class': extraction_class,
            'count': len(extractions),
            'extractions': extractions
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to get extractions'
        }), 500


@langextract_bp.route('/api/scripts/<script_id>/extractions/stats', methods=['GET'])
def get_script_extraction_stats(script_id):
    """
    Get extraction statistics for a script.
    
    Returns:
        JSON with stats per extraction class
    """
    try:
        supabase = get_supabase_client()
        stats = get_extraction_stats(script_id, supabase)
        
        # Calculate totals
        total_extractions = sum(stat['count'] for stat in stats.values())
        avg_confidence = sum(stat['avg_confidence'] * stat['count'] for stat in stats.values()) / total_extractions if total_extractions > 0 else 0
        
        return jsonify({
            'script_id': script_id,
            'total_extractions': total_extractions,
            'avg_confidence': round(avg_confidence, 2),
            'by_class': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to get extraction stats'
        }), 500


@langextract_bp.route('/api/scripts/<script_id>/visualization', methods=['GET'])
def get_script_visualization(script_id):
    """
    Get HTML visualization for a script.
    
    Returns:
        HTML content or 404 if not found
    """
    try:
        supabase = get_supabase_client()
        html_content = get_visualization(script_id, supabase)
        
        if html_content:
            return Response(html_content, mimetype='text/html')
        else:
            return jsonify({
                'error': 'Visualization not found',
                'message': 'No visualization exists for this script'
            }), 404
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to get visualization'
        }), 500


@langextract_bp.route('/api/scripts/<script_id>/extractions/by-scene/<scene_id>', methods=['GET'])
def get_scene_extractions(script_id, scene_id):
    """
    Get all extractions for a specific scene.
    
    Returns:
        JSON with extractions array
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table('extraction_metadata')\
            .select('*')\
            .eq('script_id', script_id)\
            .eq('scene_id', scene_id)\
            .order('text_start')\
            .execute()
        
        extractions = response.data if response.data else []
        
        return jsonify({
            'script_id': script_id,
            'scene_id': scene_id,
            'count': len(extractions),
            'extractions': extractions
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to get scene extractions'
        }), 500


@langextract_bp.route('/api/scripts/<script_id>/intelligence', methods=['GET'])
def get_script_intelligence(script_id):
    """
    Aggregate enrichment data across ALL scenes for script-level intelligence.
    
    Returns:
        - scenes: dict keyed by scene_id, each with enrichment counts and key items
        - totals: aggregate counts across all scenes
        - characters: character-level aggregation (scenes they appear in, dialogue count, emotions)
        - relationships: all relationships across the script
    """
    try:
        supabase = get_supabase_admin()
        
        # Fetch ALL enrichment extractions for this script
        enrichment_classes = ('emotion', 'relationship', 'transition', 'dialogue', 'action')
        response = supabase.table('extraction_metadata')\
            .select('id, scene_id, extraction_class, extraction_text, attributes, confidence')\
            .eq('script_id', script_id)\
            .in_('extraction_class', list(enrichment_classes))\
            .execute()
        
        extractions = response.data if response.data else []
        
        # Fetch scene metadata for context
        scenes_response = supabase.table('scenes')\
            .select('id, scene_number, setting, int_ext, time_of_day, atmosphere, description, characters')\
            .eq('script_id', script_id)\
            .order('scene_number')\
            .execute()
        
        scenes_data = scenes_response.data if scenes_response.data else []
        scenes_lookup = {}
        for s in scenes_data:
            sid = s['id']
            scenes_lookup[sid] = s
        
        # Group extractions by scene_id, then by class
        scene_enrichments = {}  # scene_id -> { class -> [items] }
        
        for ext in extractions:
            sid = ext.get('scene_id')
            cls = ext.get('extraction_class', 'unknown')
            if not sid:
                continue
            
            item = {
                'id': ext['id'],
                'text': ext.get('extraction_text', ''),
                'attributes': ext.get('attributes', {}),
                'confidence': ext.get('confidence', 1.0)
            }
            
            if sid not in scene_enrichments:
                scene_enrichments[sid] = {}
            if cls not in scene_enrichments[sid]:
                scene_enrichments[sid][cls] = []
            scene_enrichments[sid][cls].append(item)
        
        # Deduplicate and normalize per scene
        for sid in scene_enrichments:
            for cls in scene_enrichments[sid]:
                scene_enrichments[sid][cls] = _deduplicate_items(scene_enrichments[sid][cls])
            _normalize_character_attributes(scene_enrichments[sid])
        
        # Build per-scene summaries
        scene_summaries = []
        for s in scenes_data:
            sid = s['id']
            enrichment = scene_enrichments.get(sid, {})
            
            counts = {
                'emotions': len(enrichment.get('emotion', [])),
                'dialogue': len(enrichment.get('dialogue', [])),
                'actions': len(enrichment.get('action', [])),
                'relationships': len(enrichment.get('relationship', [])),
                'transitions': len(enrichment.get('transition', []))
            }
            total = sum(counts.values())
            
            scene_summaries.append({
                'scene_id': sid,
                'scene_number': s.get('scene_number') or '?',
                'setting': s.get('setting', ''),
                'int_ext': s.get('int_ext', ''),
                'time_of_day': s.get('time_of_day', ''),
                'emotional_tone': s.get('atmosphere', ''),
                'description': s.get('description', ''),
                'characters': s.get('characters', []),
                'counts': counts,
                'total_items': total
            })
        
        # Aggregate totals across entire script
        totals = { 'emotions': 0, 'dialogue': 0, 'actions': 0, 'relationships': 0, 'transitions': 0 }
        for ss in scene_summaries:
            for k in totals:
                totals[k] += ss['counts'].get(k, 0)
        totals['total'] = sum(totals.values())
        
        # Character-level aggregation
        char_data = {}  # canonical_name -> { scenes: set, dialogue_count, emotions: [], ... }
        
        for sid, enrichment in scene_enrichments.items():
            scene_meta = scenes_lookup.get(sid, {})
            scene_num = scene_meta.get('scene_number_original') or scene_meta.get('scene_number', '?')
            
            for d in enrichment.get('dialogue', []):
                char = (d.get('attributes', {}).get('character') or '').strip()
                if not char:
                    continue
                if char not in char_data:
                    char_data[char] = { 'scenes': set(), 'dialogue_count': 0, 'emotion_count': 0, 'action_count': 0 }
                char_data[char]['scenes'].add(str(scene_num))
                char_data[char]['dialogue_count'] += 1
            
            for e in enrichment.get('emotion', []):
                char = (e.get('attributes', {}).get('character') or '').strip()
                if not char:
                    continue
                if char not in char_data:
                    char_data[char] = { 'scenes': set(), 'dialogue_count': 0, 'emotion_count': 0, 'action_count': 0 }
                char_data[char]['scenes'].add(str(scene_num))
                char_data[char]['emotion_count'] += 1
            
            for a in enrichment.get('action', []):
                chars_attr = (a.get('attributes', {}).get('characters') or '')
                if isinstance(chars_attr, str):
                    for c in chars_attr.split(','):
                        c = c.strip()
                        if not c:
                            continue
                        if c not in char_data:
                            char_data[c] = { 'scenes': set(), 'dialogue_count': 0, 'emotion_count': 0, 'action_count': 0 }
                        char_data[c]['scenes'].add(str(scene_num))
                        char_data[c]['action_count'] += 1
        
        # Convert sets to sorted lists for JSON
        characters_agg = []
        for name, data in sorted(char_data.items()):
            characters_agg.append({
                'name': name,
                'scene_count': len(data['scenes']),
                'scenes': sorted(data['scenes'], key=lambda x: int(x) if x.isdigit() else 0),
                'dialogue_count': data['dialogue_count'],
                'emotion_count': data['emotion_count'],
                'action_count': data['action_count']
            })
        
        # All relationships across the script (deduplicated)
        all_relationships = []
        for sid, enrichment in scene_enrichments.items():
            scene_meta = scenes_lookup.get(sid, {})
            scene_num = scene_meta.get('scene_number_original') or scene_meta.get('scene_number', '?')
            for r in enrichment.get('relationship', []):
                all_relationships.append({
                    **r,
                    'scene_id': sid,
                    'scene_number': str(scene_num)
                })
        
        return jsonify({
            'script_id': script_id,
            'total_scenes': len(scenes_data),
            'totals': totals,
            'characters': characters_agg,
            'relationships': all_relationships,
            'scenes': scene_summaries
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to get script intelligence'
        }), 500


@langextract_bp.route('/api/scripts/<script_id>/scenes/<scene_id>/breakdown', methods=['GET'])
def get_scene_breakdown(script_id, scene_id):
    """
    Get rich scene breakdown from extraction_metadata, grouped by extraction_class.
    
    Returns all extractions for a scene organized into categories with full
    attributes and confidence scores — the single source of truth for scene
    breakdown data, replacing flattened JSONB arrays on the scenes table.
    
    Returns:
        JSON with breakdown object keyed by extraction_class, plus enrichment data
    """
    try:
        supabase = get_supabase_admin()
        
        # Fetch all extractions for this scene
        response = supabase.table('extraction_metadata')\
            .select('id, extraction_class, extraction_text, attributes, confidence, text_start, text_end')\
            .eq('script_id', script_id)\
            .eq('scene_id', scene_id)\
            .order('text_start')\
            .execute()
        
        extractions = response.data if response.data else []
        
        # Group by extraction_class
        breakdown = {}
        enrichment = {}
        total_confidence = 0.0
        
        for ext in extractions:
            cls = ext.get('extraction_class', 'unknown')
            item = {
                'id': ext['id'],
                'text': ext.get('extraction_text', ''),
                'attributes': ext.get('attributes', {}),
                'confidence': ext.get('confidence', 1.0),
                'text_start': ext.get('text_start'),
                'text_end': ext.get('text_end')
            }
            total_confidence += item['confidence']
            
            # Separate enrichment classes from breakdown categories
            if cls in ('emotion', 'relationship', 'transition', 'dialogue', 'action'):
                if cls not in enrichment:
                    enrichment[cls] = []
                enrichment[cls].append(item)
            else:
                # Map extraction classes to SceneDetail category keys
                category_key = _extraction_class_to_category(cls)
                if category_key:
                    if category_key not in breakdown:
                        breakdown[category_key] = []
                    breakdown[category_key].append(item)
        
        # Deduplicate items within each category (case-insensitive)
        for key in breakdown:
            breakdown[key] = _deduplicate_items(breakdown[key])
        for key in enrichment:
            enrichment[key] = _deduplicate_items(enrichment[key])
        
        # Normalize character name attributes across enrichment items
        # so "SANDRA", "Sandra", "sandra" all resolve to one canonical form
        _normalize_character_attributes(enrichment)
        
        avg_confidence = round(total_confidence / len(extractions), 2) if extractions else 0.0
        
        return jsonify({
            'script_id': script_id,
            'scene_id': scene_id,
            'total_extractions': len(extractions),
            'avg_confidence': avg_confidence,
            'breakdown': breakdown,
            'enrichment': enrichment
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to get scene breakdown'
        }), 500


def _extraction_class_to_category(cls):
    """Map extraction_class to SceneDetail category key."""
    mapping = {
        'character': 'characters',
        'prop': 'props',
        'wardrobe': 'wardrobe',
        'makeup_hair': 'makeup_hair',
        'special_fx': 'special_fx',
        'vehicle': 'vehicles',
        'location_detail': 'locations',
        'sound': 'sound',
        'scene_header': None
    }
    return mapping.get(cls, cls)


def _deduplicate_items(items):
    """
    Case-insensitive deduplication of extraction items.
    
    When duplicates exist (e.g. "Sandra", "SANDRA", "sandra"):
    - Keeps the version with highest confidence
    - Prefers Title Case display text over ALL CAPS or lowercase
    - Merges non-empty attributes from all duplicates
    """
    if not items:
        return items
    
    seen = {}  # normalized_text -> best item
    
    for item in items:
        raw_text = (item.get('text') or '').strip()
        norm = raw_text.lower()
        
        if not norm:
            continue
        
        if norm not in seen:
            seen[norm] = item.copy()
            continue
        
        existing = seen[norm]
        
        # Keep higher confidence
        if item.get('confidence', 0) > existing.get('confidence', 0):
            new_best = item.copy()
            # Merge attributes from existing into new best
            merged_attrs = {**existing.get('attributes', {})}
            for k, v in item.get('attributes', {}).items():
                if v and v != '' and v != 'unknown':
                    merged_attrs[k] = v
            new_best['attributes'] = merged_attrs
            # Prefer title-case display text
            new_best['text'] = _best_display_text(existing['text'], item['text'])
            seen[norm] = new_best
        else:
            # Merge new item's non-empty attributes into existing
            for k, v in item.get('attributes', {}).items():
                if v and v != '' and v != 'unknown':
                    existing.setdefault('attributes', {})[k] = v
            # Still prefer title-case display text
            existing['text'] = _best_display_text(existing['text'], item['text'])
    
    return list(seen.values())


def _best_display_text(a, b):
    """
    Pick the best display text between two variants.
    Preference: Title Case > Mixed > lowercase > ALL CAPS
    """
    for text in (a, b):
        t = (text or '').strip()
        if t and not t.isupper() and not t.islower():
            return t  # Title/mixed case preferred
    # Fallback: prefer non-uppercase
    a_stripped = (a or '').strip()
    b_stripped = (b or '').strip()
    if a_stripped and not a_stripped.isupper():
        return a_stripped
    if b_stripped and not b_stripped.isupper():
        return b_stripped
    # Last resort: title-case the uppercase version
    return a_stripped.title() if a_stripped else b_stripped.title()


def _normalize_character_attributes(enrichment):
    """
    Normalize character name attributes across all enrichment items so that
    case variants like "SANDRA", "Sandra", "sandra" resolve to one canonical form.
    
    Builds a canonical name map, then rewrites 'character' and 'characters'
    attribute values in-place.
    """
    if not enrichment:
        return
    
    # Phase 1: Collect all character name variants across enrichment categories
    # key = lowercased name, value = list of original-case variants
    name_variants = {}
    
    for cls_items in enrichment.values():
        for item in cls_items:
            attrs = item.get('attributes') or {}
            # Single character attribute (dialogue, emotion)
            char = attrs.get('character')
            if char and isinstance(char, str):
                char = char.strip()
                if char:
                    norm = char.lower()
                    name_variants.setdefault(norm, []).append(char)
            # Plural characters attribute (action, relationship)
            chars = attrs.get('characters')
            if chars and isinstance(chars, str):
                for c in chars.split(','):
                    c = c.strip()
                    if c:
                        norm = c.lower()
                        name_variants.setdefault(norm, []).append(c)
    
    if not name_variants:
        return
    
    # Phase 2: Pick canonical form for each name
    # Screenplays use UPPERCASE for character names — prefer that convention
    canonical = {}
    for norm, variants in name_variants.items():
        # Prefer UPPERCASE (screenplay standard), then Title Case, then first seen
        upper = next((v for v in variants if v.isupper()), None)
        if upper:
            canonical[norm] = upper
        else:
            title = next((v for v in variants if not v.isupper() and not v.islower()), None)
            canonical[norm] = title or variants[0]
    
    # Phase 3: Rewrite attributes in-place
    for cls_items in enrichment.values():
        for item in cls_items:
            attrs = item.get('attributes')
            if not attrs:
                continue
            # Normalize single 'character'
            char = attrs.get('character')
            if char and isinstance(char, str):
                norm = char.strip().lower()
                if norm in canonical:
                    attrs['character'] = canonical[norm]
            # Normalize 'characters' (comma-separated string)
            chars = attrs.get('characters')
            if chars and isinstance(chars, str):
                parts = [c.strip() for c in chars.split(',')]
                normalized_parts = []
                for c in parts:
                    norm = c.lower()
                    normalized_parts.append(canonical.get(norm, c))
                attrs['characters'] = ', '.join(normalized_parts)


@langextract_bp.route('/api/scripts/<script_id>/extractions/range', methods=['GET'])
def get_extractions_in_range(script_id):
    """
    Get extractions within a text range.
    
    Query params:
        start: Start position (required)
        end: End position (required)
    
    Returns:
        JSON with extractions array
    """
    try:
        start = request.args.get('start', type=int)
        end = request.args.get('end', type=int)
        
        if start is None or end is None:
            return jsonify({
                'error': 'Missing parameters',
                'message': 'Both start and end parameters are required'
            }), 400
        
        supabase = get_supabase_client()
        
        response = supabase.table('extraction_metadata')\
            .select('*')\
            .eq('script_id', script_id)\
            .gte('text_start', start)\
            .lte('text_end', end)\
            .order('text_start')\
            .execute()
        
        extractions = response.data if response.data else []
        
        return jsonify({
            'script_id': script_id,
            'range': {'start': start, 'end': end},
            'count': len(extractions),
            'extractions': extractions
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to get extractions in range'
        }), 500


def _run_langextract_background(script_id, script_text, job_id):
    """
    Background worker for LangExtract processing.
    Runs in a separate thread so it doesn't block Flask's request handling.
    """
    try:
        print(f"[LangExtract BG] Starting background extraction for script {script_id}, job {job_id}")
        
        result = extract_with_langextract(text=script_text)
        
        # Save extractions (use admin client to bypass RLS)
        if result['extractions']:
            supabase_admin = get_supabase_admin()
            
            # Delete previous extractions for this script before saving new ones
            try:
                supabase_admin.table('extraction_metadata')\
                    .delete()\
                    .eq('script_id', script_id)\
                    .execute()
                print(f"[LangExtract BG] Cleared old extractions for script {script_id}")
            except Exception as del_err:
                print(f"[LangExtract BG] Warning: Could not clear old extractions: {del_err}")
            
            saved_count = save_extractions_to_supabase(
                script_id=script_id,
                extractions=result['extractions'],
                supabase_client=supabase_admin,
                link_to_scenes=True
            )
            
            status = 'completed' if len(result['errors']) == 0 else 'partial'
            db = SupabaseDB()
            db.update_job_status(
                job_id,
                status,
                completed_at=datetime.now().isoformat()
            )
            
            print(f"[LangExtract BG] Completed: {saved_count} extractions saved, status={status}")
        else:
            db = SupabaseDB()
            db.update_job_status(
                job_id,
                'failed',
                completed_at=datetime.now().isoformat(),
                error_message='No extractions generated'
            )
            print(f"[LangExtract BG] Failed: No extractions generated")
        
    except Exception as e:
        import traceback
        print(f"[LangExtract BG] Error: {str(e)}")
        print(f"[LangExtract BG] Traceback: {traceback.format_exc()}")
        try:
            db = SupabaseDB()
            db.update_job_status(
                job_id,
                'failed',
                completed_at=datetime.now().isoformat(),
                error_message=str(e)
            )
        except Exception:
            pass


@langextract_bp.route('/api/scripts/<script_id>/process-langextract', methods=['POST'])
def process_with_langextract(script_id):
    """
    Process a script with LangExtract (async — returns immediately, runs in background thread).
    The frontend polls for extractions to detect completion.
    
    Returns:
        202 Accepted with job_id for tracking
    """
    try:
        supabase = get_supabase_client()
        db = SupabaseDB()
        
        # Get script text
        script_response = supabase.table('scripts')\
            .select('full_text, user_id')\
            .eq('id', script_id)\
            .single()\
            .execute()
        
        if not script_response.data:
            return jsonify({
                'error': 'Script not found',
                'message': f'No script found with id {script_id}'
            }), 404
        
        script_text = script_response.data['full_text']
        user_id = script_response.data['user_id']
        
        if not script_text:
            return jsonify({
                'error': 'No script text',
                'message': 'Script has no text content'
            }), 400
        
        # Create analysis job
        job = db.create_analysis_job(
            script_id=script_id,
            job_type='langextract',
            priority=5
        )
        
        # Update job status to processing
        db.update_job_status(job['id'], 'processing', started_at=datetime.now().isoformat())
        
        # Run extraction in background thread so we don't block Flask
        thread = threading.Thread(
            target=_run_langextract_background,
            args=(script_id, script_text, job['id']),
            daemon=True
        )
        thread.start()
        
        print(f"[LangExtract] Background thread started for script {script_id} ({len(script_text)} chars)")
        
        return jsonify({
            'script_id': script_id,
            'job_id': job['id'],
            'status': 'processing',
            'message': f'Extraction started in background ({len(script_text)} chars)',
            'text_length': len(script_text)
        }), 202
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[LangExtract Error] {str(e)}")
        print(f"[LangExtract Traceback] {error_trace}")
        
        return jsonify({
            'error': str(e),
            'message': 'Failed to process script with LangExtract',
            'details': error_trace if os.getenv('FLASK_ENV') == 'development' else None
        }), 500


@langextract_bp.route('/api/scripts/<script_id>/process-langextract-stream', methods=['POST'])
def process_with_langextract_stream(script_id):
    """
    Process a script with LangExtract using Server-Sent Events for real-time progress.
    
    Returns:
        SSE stream with progress updates
    """
    def generate():
        try:
            supabase = get_supabase_client()
            db = SupabaseDB()
            
            # Mark extraction as active
            _active_extractions[script_id] = {'cancelled': False}
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Initializing', 'progress': 0})}\n\n"
            
            # Get script text
            script_response = supabase.table('scripts')\
                .select('full_text, user_id')\
                .eq('id', script_id)\
                .single()\
                .execute()
            
            if not script_response.data:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Script not found'})}\n\n"
                return
            
            script_text = script_response.data['full_text']
            
            if not script_text:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No script text'})}\n\n"
                return
            
            # Create analysis job
            job = db.create_analysis_job(
                script_id=script_id,
                job_type='langextract',
                priority=5
            )
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Job created', 'progress': 5, 'job_id': job['id']})}\n\n"
            
            # Update job status
            db.update_job_status(job['id'], 'processing', started_at=time.time())
            
            # Progress callback for SSE
            def progress_callback(percentage: int, message: str):
                if _active_extractions.get(script_id, {}).get('cancelled'):
                    raise Exception("Extraction cancelled by user")
                return f"data: {json.dumps({'type': 'progress', 'progress': percentage, 'message': message})}\n\n"
            
            # Send progress updates
            for pct in [10, 20, 30]:
                if _active_extractions.get(script_id, {}).get('cancelled'):
                    yield f"data: {json.dumps({'type': 'cancelled', 'message': 'Extraction cancelled'})}\n\n"
                    return
                yield progress_callback(pct, f"Processing ({pct}%)")
            
            # Process with LangExtract
            result = extract_with_langextract(
                text=script_text,
                progress_callback=lambda p, m: None  # Callback handled above
            )
            
            if _active_extractions.get(script_id, {}).get('cancelled'):
                yield f"data: {json.dumps({'type': 'cancelled', 'message': 'Extraction cancelled'})}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'progress', 'progress': 80, 'message': 'Saving extractions'})}\n\n"
            
            # Save extractions
            if result['extractions']:
                saved_count = save_extractions_to_supabase(
                    script_id=script_id,
                    extractions=result['extractions'],
                    supabase_client=supabase,
                    link_to_scenes=True
                )
                
                status = 'completed' if len(result['errors']) == 0 else 'partial'
                db.update_job_status(
                    job['id'],
                    status,
                    completed_at=time.time(),
                    result_data={
                        'stats': result['stats'],
                        'errors': result['errors'],
                        'saved_count': saved_count
                    }
                )
                
                yield f"data: {json.dumps({'type': 'progress', 'progress': 100, 'message': 'Complete'})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'status': status, 'extractions_saved': saved_count, 'stats': result['stats'], 'errors': result['errors']})}\n\n"
            else:
                db.update_job_status(
                    job['id'],
                    'failed',
                    completed_at=time.time(),
                    error_message='No extractions generated'
                )
                yield f"data: {json.dumps({'type': 'error', 'message': 'No extractions generated', 'errors': result['errors']})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Clean up active extraction tracking
            if script_id in _active_extractions:
                del _active_extractions[script_id]
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@langextract_bp.route('/api/scripts/<script_id>/extractions/cancel', methods=['POST'])
def cancel_extraction(script_id):
    """
    Cancel an in-progress LangExtract extraction.
    
    Returns:
        JSON with cancellation status
    """
    if script_id in _active_extractions:
        _active_extractions[script_id]['cancelled'] = True
        
        # Update job status in database
        try:
            db = SupabaseDB()
            supabase = get_supabase_client()
            
            # Find the most recent processing job for this script
            jobs = supabase.table('analysis_jobs')\
                .select('*')\
                .eq('script_id', script_id)\
                .eq('job_type', 'langextract')\
                .eq('status', 'processing')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if jobs.data:
                job_id = jobs.data[0]['id']
                db.update_job_status(
                    job_id,
                    'cancelled',
                    completed_at=time.time(),
                    error_message='Cancelled by user'
                )
        except Exception as e:
            print(f"[LangExtract] Failed to update job status: {str(e)}")
        
        return jsonify({
            'script_id': script_id,
            'status': 'cancelled',
            'message': 'Extraction cancellation requested'
        }), 200
    else:
        return jsonify({
            'script_id': script_id,
            'status': 'not_found',
            'message': 'No active extraction found for this script'
        }), 404


@langextract_bp.route('/api/scripts/<script_id>/extractions/job-status', methods=['GET'])
def get_extraction_job_status(script_id):
    """
    Get the status of the most recent LangExtract job for a script.
    Used by the frontend to detect completion or failure.
    
    Returns:
        JSON with job status, error_message if failed
    """
    try:
        supabase = get_supabase_client()
        
        jobs = supabase.table('analysis_jobs')\
            .select('id, status, error_message, created_at, completed_at')\
            .eq('script_id', script_id)\
            .eq('job_type', 'langextract')\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if not jobs.data:
            return jsonify({
                'script_id': script_id,
                'status': 'none',
                'message': 'No extraction jobs found'
            }), 200
        
        job = jobs.data[0]
        return jsonify({
            'script_id': script_id,
            'job_id': job['id'],
            'status': job['status'],
            'error_message': job.get('error_message'),
            'created_at': job.get('created_at'),
            'completed_at': job.get('completed_at')
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to get job status'
        }), 500


@langextract_bp.route('/api/extractions/classes', methods=['GET'])
def get_extraction_classes():
    """
    Get list of all available extraction classes.
    
    Returns:
        JSON with extraction classes and their descriptions
    """
    from services.langextract_schema import SCREENPLAY_EXTRACTION_SCHEMA
    
    classes = []
    for class_name, class_def in SCREENPLAY_EXTRACTION_SCHEMA.items():
        classes.append({
            'name': class_name,
            'description': class_def.description,
            'attributes': class_def.attributes,
            'example_count': len(class_def.examples)
        })
    
    return jsonify({
        'count': len(classes),
        'classes': classes
    }), 200


@langextract_bp.route('/api/scripts/<script_id>/highlighted-pdf', methods=['POST'])
def generate_highlighted_pdf_endpoint(script_id):
    """
    Generate a highlighted script PDF with extraction overlays.
    
    Body (optional):
        filter_classes: List of extraction_class values to include (null = all)
    
    Returns:
        PDF file as attachment
    """
    try:
        from services.highlighted_script_service import generate_highlighted_pdf

        body = request.get_json(silent=True) or {}
        filter_classes = body.get('filter_classes', None)

        # Validate filter_classes if provided
        if filter_classes is not None:
            if not isinstance(filter_classes, list):
                return jsonify({
                    'error': 'filter_classes must be an array of strings'
                }), 400
            from services.langextract_schema import SCREENPLAY_EXTRACTION_SCHEMA
            valid_classes = set(SCREENPLAY_EXTRACTION_SCHEMA.keys())
            invalid = [c for c in filter_classes if c not in valid_classes]
            if invalid:
                return jsonify({
                    'error': f'Invalid extraction classes: {invalid}',
                    'valid_classes': list(valid_classes)
                }), 400

        pdf_bytes, filename = generate_highlighted_pdf(
            script_id=script_id,
            filter_classes=filter_classes
        )

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(len(pdf_bytes))
            }
        )

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except ImportError as e:
        return jsonify({
            'error': 'PDF generation unavailable',
            'message': str(e)
        }), 503
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[HighlightedPDF Error] {str(e)}")
        print(f"[HighlightedPDF Traceback] {error_trace}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to generate highlighted PDF'
        }), 500


@langextract_bp.route('/api/scripts/<script_id>/highlighted-html', methods=['POST'])
def generate_highlighted_html_endpoint(script_id):
    """
    Generate highlighted script as printable HTML.
    
    Body (optional):
        filter_classes: List of extraction_class values to include (null = all)
    
    Returns:
        HTML content for browser-side printing
    """
    try:
        from services.highlighted_script_service import generate_highlighted_html

        body = request.get_json(silent=True) or {}
        filter_classes = body.get('filter_classes', None)

        html_content = generate_highlighted_html(
            script_id=script_id,
            filter_classes=filter_classes
        )

        return Response(
            html_content,
            mimetype='text/html',
            headers={'Content-Type': 'text/html; charset=utf-8'}
        )

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        import traceback
        print(f"[HighlightedHTML Error] {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to generate highlighted HTML'
        }), 500


@langextract_bp.route('/api/scripts/<script_id>/highlighted-pdf/classes', methods=['GET'])
def get_available_highlight_classes(script_id):
    """
    Get extraction classes available for this script (classes that have data).
    Useful for building a filter UI before generating the highlighted PDF.
    
    Returns:
        JSON with available classes and their counts
    """
    try:
        # Use admin client to bypass RLS (consistent with other extraction endpoints)
        supabase = get_supabase_admin()

        response = supabase.table('extraction_metadata')\
            .select('extraction_class')\
            .eq('script_id', script_id)\
            .execute()

        if not response.data:
            return jsonify({
                'script_id': script_id,
                'classes': [],
                'total': 0
            }), 200

        # Count per class
        counts = {}
        for row in response.data:
            cls = row['extraction_class']
            counts[cls] = counts.get(cls, 0) + 1

        from services.highlighted_script_service import HIGHLIGHT_COLORS, DEFAULT_HIGHLIGHT

        classes = []
        for cls, count in sorted(counts.items(), key=lambda x: -x[1]):
            colors = HIGHLIGHT_COLORS.get(cls, DEFAULT_HIGHLIGHT)
            classes.append({
                'class': cls,
                'label': colors['label'],
                'color': colors['border'],
                'count': count
            })

        return jsonify({
            'script_id': script_id,
            'classes': classes,
            'total': sum(counts.values())
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
