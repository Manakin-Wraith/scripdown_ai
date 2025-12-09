from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import time
from services.script_service import process_script, process_script_v2, analyze_script_async
from services.analysis_service import analyze_characters, analyze_locations, clear_analysis_cache
from services.analysis_queue_service import queue_full_analysis
from db.db_connection import get_db

script_bp = Blueprint('script', __name__)


@script_bp.route('/upload_script', methods=['POST'])
def upload_script():
    """
    Upload a script using the new page-based pipeline.
    
    Phase 1 (this endpoint):
    - Parse PDF with page awareness
    - Detect scene headers via regex
    - Create scene candidates
    - Extract metadata
    
    Phase 2 (user-triggered):
    - User manually triggers analysis per scene or bulk
    - No automatic AI analysis on upload
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        try:
            # Use new v2 pipeline - fast regex extraction only
            result = process_script_v2(file)
            script_id = result['script_id']
            
            # NO automatic analysis queuing - user controls when to analyze
            # This makes upload instant and gives user control
            
            return jsonify({
                'message': 'Script uploaded successfully',
                'script_id': script_id,
                'total_pages': result.get('total_pages', 0),
                'scene_candidates': result.get('scene_candidates', 0),
                'status': 'ready_for_analysis'  # User must trigger analysis
            }), 201
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500


@script_bp.route('/upload_script_legacy', methods=['POST'])
def upload_script_legacy():
    """Legacy upload endpoint (old pipeline)."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        try:
            script_id = process_script(file)
            
            # Auto-queue full AI analysis
            try:
                queue_full_analysis(script_id, priority=5)
                analysis_status = 'analysis_queued'
            except Exception as analysis_err:
                print(f"Warning: Failed to queue analysis: {analysis_err}")
                analysis_status = 'ready_for_analysis'
            
            return jsonify({
                'message': 'Script uploaded successfully',
                'script_id': script_id,
                'status': analysis_status
            }), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@script_bp.route('/analyze_script/<int:script_id>', methods=['POST'])
def analyze_script_endpoint(script_id):
    """Analyze script with AI in background."""
    try:
        scene_count = analyze_script_async(script_id)
        return jsonify({
            'message': 'Analysis complete',
            'script_id': script_id,
            'scenes_extracted': scene_count
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@script_bp.route('/analyze_script_stream/<int:script_id>')
def analyze_script_stream(script_id):
    """Stream analysis progress using Server-Sent Events."""
    def generate():
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Get script text
            cursor.execute("SELECT script_text FROM scripts WHERE script_id = ?", (script_id,))
            row = cursor.fetchone()
            
            if not row:
                yield f"data: {json.dumps({'error': 'Script not found'})}\n\n"
                return
            
            script_text = row[0]
            cursor.close()
            
            # Send initial progress
            yield f"data: {json.dumps({'progress': 0, 'status': 'Starting analysis...'})}\n\n"
            time.sleep(0.5)
            
            # Import here to avoid circular imports
            from services.gemini_service import analyze_script
            
            # Analyze script with progress updates
            yield f"data: {json.dumps({'progress': 10, 'status': 'Sending script to AI...'})}\n\n"
            time.sleep(0.5)
            
            yield f"data: {json.dumps({'progress': 15, 'status': 'AI is analyzing the script...'})}\n\n"
            time.sleep(1)
            
            yield f"data: {json.dumps({'progress': 20, 'status': 'Extracting scenes and characters...'})}\n\n"
            
            # Call AI (this is the slow part)
            analysis = analyze_script(script_text)
            
            if 'error' in analysis:
                yield f"data: {json.dumps({'error': analysis['error']})}\n\n"
                return
            
            scenes = analysis.get('scenes', [])
            total_scenes = len(scenes)
            
            if total_scenes == 0:
                yield f"data: {json.dumps({'progress': 100, 'status': 'No scenes found', 'scenes_extracted': 0})}\n\n"
                return
            
            yield f"data: {json.dumps({'progress': 30, 'status': f'Found {total_scenes} scenes! Saving to database...'})}\n\n"
            time.sleep(0.5)
            
            # Save scenes in chunks of 10
            from services.script_service import save_scene
            chunk_size = 10
            
            for i, scene_data in enumerate(scenes):
                save_scene(script_id, scene_data)
                
                # Send progress update every 10 scenes or at the end
                if (i + 1) % chunk_size == 0 or (i + 1) == total_scenes:
                    progress = 30 + int((i + 1) / total_scenes * 70)
                    yield f"data: {json.dumps({'progress': progress, 'status': f'Saved {i + 1}/{total_scenes} scenes...'})}\n\n"
                    time.sleep(0.2)  # Slightly longer delay for visibility
            
            # Final completion message
            yield f"data: {json.dumps({'progress': 100, 'status': 'Analysis complete!', 'scenes_extracted': total_scenes, 'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@script_bp.route('/get_scenes/<int:script_id>', methods=['GET'])
def get_scenes(script_id):
    """Get all scenes for a script with detailed breakdown."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        query = """
            SELECT scene_id, scene_number, scene_number_original,
                   page_start, page_end,
                   setting, description, 
                   characters, props, special_fx, wardrobe, 
                   makeup_hair, vehicles, atmosphere
            FROM scenes
            WHERE script_id = ?
            ORDER BY scene_number
        """
        cursor.execute(query, (script_id,))
        rows = cursor.fetchall()
        
        scenes = []
        for row in rows:
            scenes.append({
                'scene_id': row[0],
                'scene_number': row[1],
                'scene_number_original': row[2],
                'page_start': row[3],
                'page_end': row[4],
                'setting': row[5],
                'description': row[6],
                'characters': json.loads(row[7]) if row[7] else [],
                'props': json.loads(row[8]) if row[8] else [],
                'special_fx': json.loads(row[9]) if row[9] else [],
                'wardrobe': json.loads(row[10]) if row[10] else [],
                'makeup_hair': json.loads(row[11]) if row[11] else [],
                'vehicles': json.loads(row[12]) if row[12] else [],
                'atmosphere': row[13] if row[13] else ''
            })
        
        cursor.close()
        return jsonify({'script_id': script_id, 'scenes': scenes}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@script_bp.route('/get_breakdown_data', methods=['GET'])
def get_breakdown_data():
    script_id = request.args.get('script_id')
    role = request.args.get('role')

    if not script_id or not role:
        return jsonify({'error': 'Missing script_id or role'}), 400

    # TODO: Implement role-specific data filtering
    # For now, return all scenes
    try:
        db = get_db()
        cursor = db.cursor()
        
        query = """
            SELECT scene_id, scene_number, scene_number_original,
                   page_start, page_end,
                   setting, description, 
                   characters, props, special_fx, wardrobe, 
                   makeup_hair, vehicles, atmosphere
            FROM scenes
            WHERE script_id = ?
            ORDER BY scene_number
        """
        cursor.execute(query, (script_id,))
        rows = cursor.fetchall()
        
        scenes = []
        for row in rows:
            scenes.append({
                'scene_id': row[0],
                'scene_number': row[1],
                'scene_number_original': row[2],
                'page_start': row[3],
                'page_end': row[4],
                'setting': row[5],
                'description': row[6],
                'characters': json.loads(row[7]) if row[7] else [],
                'props': json.loads(row[8]) if row[8] else [],
                'special_fx': json.loads(row[9]) if row[9] else [],
                'wardrobe': json.loads(row[10]) if row[10] else [],
                'makeup_hair': json.loads(row[11]) if row[11] else [],
                'vehicles': json.loads(row[12]) if row[12] else [],
                'atmosphere': row[13] if row[13] else ''
            })
        
        cursor.close()
        return jsonify({
            'script_id': script_id,
            'role': role,
            'scenes': scenes
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@script_bp.route('/scripts', methods=['GET'])
def get_all_scripts():
    """Get all uploaded scripts with metadata."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get scripts with scene count and writer name
        query = """
            SELECT 
                s.script_id,
                s.script_name,
                s.upload_date,
                s.writer_name,
                COUNT(sc.scene_id) as scene_count
            FROM scripts s
            LEFT JOIN scenes sc ON s.script_id = sc.script_id
            GROUP BY s.script_id
            ORDER BY s.upload_date DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        scripts = []
        for row in rows:
            scripts.append({
                'script_id': row[0],
                'script_name': row[1],
                'upload_date': row[2],
                'writer_name': row[3],
                'scene_count': row[4],
                'status': 'analyzed' if row[4] > 0 else 'pending'
            })
        
        cursor.close()
        return jsonify({'scripts': scripts}), 200
        
    except Exception as e:
        print(f"Error in get_all_scripts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@script_bp.route('/scripts/<int:script_id>', methods=['DELETE'])
def delete_script(script_id):
    """Delete a script and all related data."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if script exists
        cursor.execute("SELECT script_name FROM scripts WHERE script_id = ?", (script_id,))
        script = cursor.fetchone()
        
        if not script:
            return jsonify({'error': 'Script not found'}), 404
        
        # Delete all related data (explicit cascade)
        cursor.execute("DELETE FROM analysis_jobs WHERE script_id = ?", (script_id,))
        cursor.execute("DELETE FROM scene_candidates WHERE script_id = ?", (script_id,))
        cursor.execute("DELETE FROM script_pages WHERE script_id = ?", (script_id,))
        cursor.execute("DELETE FROM scenes WHERE script_id = ?", (script_id,))
        cursor.execute("DELETE FROM character_analysis WHERE script_id = ?", (script_id,))
        cursor.execute("DELETE FROM story_arc_analysis WHERE script_id = ?", (script_id,))
        cursor.execute("DELETE FROM script_analysis WHERE script_id = ?", (script_id,))
        cursor.execute("DELETE FROM location_analysis WHERE script_id = ?", (script_id,))
        
        # Finally delete the script
        cursor.execute("DELETE FROM scripts WHERE script_id = ?", (script_id,))
        db.commit()
        cursor.close()
        
        return jsonify({
            'message': f'Script "{script[0]}" deleted successfully',
            'script_id': script_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@script_bp.route('/scripts/<int:script_id>/reanalyze', methods=['POST'])
def reanalyze_script(script_id):
    """Delete existing scenes and prepare for re-analysis."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if script exists
        cursor.execute("SELECT script_name FROM scripts WHERE script_id = ?", (script_id,))
        script = cursor.fetchone()
        
        if not script:
            return jsonify({'error': 'Script not found'}), 404
        
        # Delete existing scenes
        cursor.execute("DELETE FROM scenes WHERE script_id = ?", (script_id,))
        db.commit()
        cursor.close()
        
        return jsonify({
            'message': 'Ready for re-analysis',
            'script_id': script_id,
            'script_name': script[0]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@script_bp.route('/scripts/<int:script_id>/metadata', methods=['GET'])
def get_script_metadata(script_id):
    """Get metadata for a specific script."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        query = """
            SELECT 
                script_id,
                script_name,
                writer_name,
                writer_email,
                writer_phone,
                draft_version,
                draft_date,
                copyright_info,
                wga_registration,
                additional_credits,
                upload_date
            FROM scripts
            WHERE script_id = ?
        """
        cursor.execute(query, (script_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'error': 'Script not found'}), 404
        
        metadata = {
            'script_id': row[0],
            'script_name': row[1],
            'writer_name': row[2],
            'writer_email': row[3],
            'writer_phone': row[4],
            'draft_version': row[5],
            'draft_date': row[6],
            'copyright_info': row[7],
            'wga_registration': row[8],
            'additional_credits': row[9],
            'upload_date': row[10]
        }
        
        cursor.close()
        return jsonify(metadata), 200
        
    except Exception as e:
        print(f"Error in get_script_metadata: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@script_bp.route('/scripts/<int:script_id>/analyze/characters', methods=['POST'])
def analyze_characters_endpoint(script_id):
    """Analyze characters using Gemini AI."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get scenes for this script
        query = """
            SELECT scene_id, scene_number, setting, description, characters
            FROM scenes
            WHERE script_id = ?
            ORDER BY scene_number
        """
        cursor.execute(query, (script_id,))
        rows = cursor.fetchall()
        
        if not rows:
            return jsonify({'error': 'No scenes found for this script'}), 404
        
        # Build scenes list and aggregate characters
        scenes = []
        characters = {}
        
        for row in rows:
            scene = {
                'scene_id': row[0],
                'scene_number': row[1],
                'setting': row[2],
                'description': row[3],
                'characters': json.loads(row[4]) if row[4] else []
            }
            scenes.append(scene)
            
            # Aggregate characters
            for char in scene['characters']:
                if char not in characters:
                    characters[char] = []
                characters[char].append(scene)
        
        cursor.close()
        
        if not characters:
            return jsonify({'error': 'No characters found in scenes'}), 404
        
        # Analyze with Gemini
        result = analyze_characters(script_id, characters, scenes)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in analyze_characters: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@script_bp.route('/scripts/<int:script_id>/analyze/locations', methods=['POST'])
def analyze_locations_endpoint(script_id):
    """Analyze locations using Gemini AI."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get scenes for this script
        query = """
            SELECT scene_id, scene_number, setting, description, characters
            FROM scenes
            WHERE script_id = ?
            ORDER BY scene_number
        """
        cursor.execute(query, (script_id,))
        rows = cursor.fetchall()
        
        if not rows:
            return jsonify({'error': 'No scenes found for this script'}), 404
        
        # Build scenes list and aggregate locations
        scenes = []
        locations = {}
        
        for row in rows:
            scene = {
                'scene_id': row[0],
                'scene_number': row[1],
                'setting': row[2],
                'description': row[3],
                'characters': json.loads(row[4]) if row[4] else []
            }
            scenes.append(scene)
            
            # Aggregate locations
            if scene['setting']:
                setting = scene['setting']
                if setting not in locations:
                    locations[setting] = []
                locations[setting].append(scene)
        
        cursor.close()
        
        if not locations:
            return jsonify({'error': 'No locations found in scenes'}), 404
        
        # Analyze with Gemini
        result = analyze_locations(script_id, locations, scenes)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in analyze_locations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@script_bp.route('/scripts/<int:script_id>/analysis/clear', methods=['POST'])
def clear_analysis_endpoint(script_id):
    """Clear cached analysis for a script."""
    try:
        clear_analysis_cache(script_id)
        return jsonify({'message': 'Analysis cache cleared', 'script_id': script_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@script_bp.route('/scenes/<int:scene_id>/analyze', methods=['POST'])
def analyze_single_scene(scene_id):
    """
    Analyze a single scene on-demand.
    
    This allows users to selectively analyze scenes instead of
    processing the entire script at once.
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get scene and script info
        cursor.execute("""
            SELECT s.script_id, s.scene_number, sc.script_text
            FROM scenes s
            JOIN scripts sc ON s.script_id = sc.script_id
            WHERE s.scene_id = ?
        """, (scene_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'error': 'Scene not found'}), 404
        
        script_id, scene_number = row[0], row[1]
        
        # Check if scene is already analyzed (has breakdown data)
        cursor.execute("""
            SELECT props, wardrobe, special_fx, vehicles
            FROM scenes WHERE scene_id = ?
        """, (scene_id,))
        scene_data = cursor.fetchone()
        
        # Queue single scene enhancement
        from services.analysis_queue_service import create_analysis_job
        
        job_id = create_analysis_job(
            script_id,
            'single_scene',
            scene_id,  # target_id is the scene_id
            priority=1  # High priority for user-triggered
        )
        
        cursor.close()
        
        return jsonify({
            'message': 'Scene analysis queued',
            'scene_id': scene_id,
            'script_id': script_id,
            'scene_number': scene_number,
            'job_id': job_id
        }), 200
        
    except Exception as e:
        print(f"Error in analyze_single_scene: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@script_bp.route('/scripts/<int:script_id>/analyze/bulk', methods=['POST'])
def analyze_bulk_scenes(script_id):
    """
    Analyze all pending scenes for a script.
    
    This is the "Analyze All" functionality, hidden but available.
    """
    try:
        from services.analysis_queue_service import queue_scene_enhancement
        
        result = queue_scene_enhancement(script_id, priority=3, force=True)
        
        if result:
            return jsonify({
                'message': 'Bulk analysis queued',
                'script_id': script_id,
                'jobs_created': result.get('jobs_created', 0),
                'scene_candidates': result.get('scene_candidates', 0)
            }), 200
        else:
            return jsonify({'error': 'Failed to queue analysis'}), 500
            
    except Exception as e:
        print(f"Error in analyze_bulk_scenes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@script_bp.route('/scripts/<int:script_id>/scenes/status', methods=['GET'])
def get_scenes_analysis_status(script_id):
    """
    Get analysis status for all scenes in a script.
    
    Returns which scenes are pending, analyzing, or complete.
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get all scenes with their analysis status
        cursor.execute("""
            SELECT 
                scene_id,
                scene_number,
                scene_number_original,
                setting,
                CASE 
                    WHEN props IS NOT NULL AND props != '[]' THEN 'complete'
                    ELSE 'pending'
                END as analysis_status
            FROM scenes
            WHERE script_id = ?
            ORDER BY scene_number
        """, (script_id,))
        
        rows = cursor.fetchall()
        
        scenes_status = []
        for row in rows:
            scenes_status.append({
                'scene_id': row[0],
                'scene_number': row[1],
                'scene_number_original': row[2],
                'setting': row[3],
                'analysis_status': row[4]
            })
        
        # Count stats
        total = len(scenes_status)
        complete = sum(1 for s in scenes_status if s['analysis_status'] == 'complete')
        pending = total - complete
        
        cursor.close()
        
        return jsonify({
            'script_id': script_id,
            'scenes': scenes_status,
            'stats': {
                'total': total,
                'complete': complete,
                'pending': pending,
                'progress': round(complete / total * 100) if total > 0 else 0
            }
        }), 200
        
    except Exception as e:
        print(f"Error in get_scenes_analysis_status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@script_bp.route('/scripts/<int:script_id>/detect-scenes-ai', methods=['POST'])
def detect_scenes_with_ai(script_id):
    """
    Use AI to detect scenes in scripts without standard headers.
    
    This is a fallback for scripts that don't use INT./EXT. format.
    The AI will analyze the document and identify scene breaks.
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get script info
        cursor.execute("""
            SELECT script_id, script_name, file_path 
            FROM scripts 
            WHERE script_id = ?
        """, (script_id,))
        script = cursor.fetchone()
        
        if not script:
            return jsonify({'error': 'Script not found'}), 404
        
        script_id, script_name, file_path = script
        
        # Get full text from pages table
        cursor.execute("""
            SELECT page_text FROM script_pages 
            WHERE script_id = ? 
            ORDER BY page_number
        """, (script_id,))
        pages = cursor.fetchall()
        
        if not pages:
            # Fallback: try to read from file
            if file_path and os.path.exists(file_path):
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                full_text = "\n".join([page.get_text() for page in doc])
                doc.close()
            else:
                return jsonify({'error': 'No script content found'}), 400
        else:
            full_text = "\n".join([p[0] for p in pages if p[0]])
        
        if not full_text or len(full_text) < 100:
            return jsonify({'error': 'Script content too short'}), 400
        
        # Use AI to detect scene breaks
        from services.ai_scene_detector import detect_scenes_with_ai as ai_detect
        
        scenes_detected = ai_detect(script_id, full_text)
        
        return jsonify({
            'success': True,
            'script_id': script_id,
            'scenes_detected': scenes_detected,
            'message': f'AI detected {scenes_detected} scenes'
        }), 200
        
    except ImportError:
        # AI detector not implemented yet - use simple fallback
        return detect_scenes_simple_fallback(script_id)
    except Exception as e:
        print(f"Error in detect_scenes_with_ai: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def detect_scenes_simple_fallback(script_id):
    """
    Simple fallback scene detection when AI is not available.
    Creates scenes based on page breaks or paragraph patterns.
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get pages
        cursor.execute("""
            SELECT page_number, page_text 
            FROM script_pages 
            WHERE script_id = ? 
            ORDER BY page_number
        """, (script_id,))
        pages = cursor.fetchall()
        
        if not pages:
            return jsonify({'error': 'No pages found'}), 400
        
        scenes_created = 0
        
        # Create one scene per page as fallback
        for page_num, page_text in pages:
            if not page_text or len(page_text.strip()) < 50:
                continue
            
            # Check if scene already exists for this page
            cursor.execute("""
                SELECT scene_id FROM scenes 
                WHERE script_id = ? AND page_start = ?
            """, (script_id, page_num))
            
            if cursor.fetchone():
                continue
            
            # Create scene candidate
            cursor.execute("""
                INSERT INTO scenes (
                    script_id, scene_number, int_ext, setting, 
                    time_of_day, page_start, page_end, scene_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                script_id,
                str(page_num),
                'INT',
                f'Page {page_num}',
                'DAY',
                page_num,
                page_num,
                page_text[:2000]  # Limit text length
            ))
            scenes_created += 1
        
        db.commit()
        
        return jsonify({
            'success': True,
            'script_id': script_id,
            'scenes_detected': scenes_created,
            'message': f'Created {scenes_created} page-based scenes (AI fallback)',
            'fallback': True
        }), 200
        
    except Exception as e:
        print(f"Error in fallback scene detection: {e}")
        return jsonify({'error': str(e)}), 500


@script_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Total scripts
        cursor.execute("SELECT COUNT(*) FROM scripts")
        total_scripts = cursor.fetchone()[0]
        
        # Total scenes
        cursor.execute("SELECT COUNT(*) FROM scenes")
        total_scenes = cursor.fetchone()[0]
        
        # Analyzed scripts (scripts with scenes)
        cursor.execute("""
            SELECT COUNT(DISTINCT script_id) 
            FROM scenes
        """)
        analyzed_scripts = cursor.fetchone()[0]
        
        # Pending scripts (scripts without scenes)
        pending_scripts = total_scripts - analyzed_scripts
        
        # Recent scripts (last 3)
        cursor.execute("""
            SELECT 
                s.script_id,
                s.script_name,
                s.upload_date,
                s.writer_name,
                COUNT(sc.scene_id) as scene_count
            FROM scripts s
            LEFT JOIN scenes sc ON s.script_id = sc.script_id
            GROUP BY s.script_id
            ORDER BY s.upload_date DESC
            LIMIT 3
        """)
        recent_rows = cursor.fetchall()
        
        recent_scripts = []
        for row in recent_rows:
            recent_scripts.append({
                'script_id': row[0],
                'script_name': row[1],
                'upload_date': row[2],
                'writer_name': row[3],
                'scene_count': row[4],
                'status': 'analyzed' if row[4] > 0 else 'pending'
            })
        
        cursor.close()
        
        return jsonify({
            'total_scripts': total_scripts,
            'total_scenes': total_scenes,
            'analyzed_scripts': analyzed_scripts,
            'pending_scripts': pending_scripts,
            'recent_scripts': recent_scripts
        }), 200
        
    except Exception as e:
        print(f"Error in get_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500




