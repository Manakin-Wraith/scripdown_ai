"""
Analysis API Routes - Endpoints for managing AI analysis jobs.

Endpoints:
- GET  /api/analysis/status - Get all scripts analysis status
- GET  /api/scripts/<id>/analysis/status - Get script analysis status
- POST /api/scripts/<id>/analysis/start - Start full analysis for a script
- POST /api/scripts/<id>/analysis/retry - Retry failed analyses
- GET  /api/scripts/<id>/analysis/characters - Get all character analyses
- GET  /api/scripts/<id>/analysis/characters/<name> - Get specific character analysis
- GET  /api/scripts/<id>/analysis/story-arc - Get story arc analysis
"""

from flask import Blueprint, jsonify, request
from services.analysis_queue_service import (
    get_script_analysis_status,
    get_all_analysis_status,
    queue_full_analysis,
    cancel_script_analysis,
    get_character_analysis,
    get_all_character_analyses,
    get_story_arc_analysis,
    create_analysis_job
)
from services.analysis_worker import start_worker
from db.db_connection import get_db

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/api/analysis/status', methods=['GET'])
def get_global_analysis_status():
    """Get analysis status for all scripts."""
    try:
        status = get_all_analysis_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/scripts/<int:script_id>/analysis/status', methods=['GET'])
def get_script_status(script_id):
    """Get detailed analysis status for a specific script."""
    try:
        status = get_script_analysis_status(script_id)
        
        if not status:
            return jsonify({
                'success': False,
                'error': 'Script not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/scripts/<int:script_id>/analysis/start', methods=['POST'])
def start_script_analysis(script_id):
    """Start full analysis for a script."""
    try:
        # Get priority from request (optional)
        data = request.get_json() or {}
        priority = data.get('priority', 5)
        
        # Ensure worker is running
        start_worker()
        
        # Queue the analysis
        result = queue_full_analysis(script_id, priority)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Failed to queue analysis'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Analysis queued successfully',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/scripts/<int:script_id>/analysis/retry', methods=['POST'])
def retry_script_analysis(script_id):
    """Retry failed analyses for a script."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get failed jobs
        cursor.execute("""
            SELECT job_id, job_type, target_id 
            FROM analysis_jobs 
            WHERE script_id = ? AND status = 'failed'
        """, (script_id,))
        
        failed_jobs = cursor.fetchall()
        
        # Re-queue them
        for job in failed_jobs:
            cursor.execute("""
                UPDATE analysis_jobs 
                SET status = 'queued', 
                    retry_count = retry_count + 1,
                    error_message = NULL,
                    started_at = NULL,
                    completed_at = NULL
                WHERE job_id = ?
            """, (job[0],))
        
        db.commit()
        cursor.close()
        
        # Ensure worker is running
        start_worker()
        
        return jsonify({
            'success': True,
            'message': f'Re-queued {len(failed_jobs)} failed jobs'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/scripts/<int:script_id>/analysis/cancel', methods=['POST'])
def cancel_analysis(script_id):
    """Cancel all pending/processing analysis jobs for a script."""
    try:
        result = cancel_script_analysis(script_id)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Failed to cancel analysis'
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'Cancelled {result["cancelled_jobs"]} jobs',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/scripts/<int:script_id>/analysis/characters', methods=['GET'])
def get_characters_analysis(script_id):
    """Get all character analyses for a script."""
    try:
        characters = get_all_character_analyses(script_id)
        
        # Also get story arc for context
        story_arc = get_story_arc_analysis(script_id)
        
        return jsonify({
            'success': True,
            'data': {
                'characters': characters,
                'story_arc': story_arc
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/scripts/<int:script_id>/analysis/characters/<character_name>', methods=['GET'])
def get_single_character_analysis(script_id, character_name):
    """Get analysis for a specific character."""
    try:
        from urllib.parse import unquote
        decoded_name = unquote(character_name)
        
        analysis = get_character_analysis(script_id, decoded_name)
        
        if not analysis:
            return jsonify({
                'success': False,
                'error': f'No analysis found for character: {decoded_name}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/scripts/<int:script_id>/analysis/story-arc', methods=['GET'])
def get_story_arc(script_id):
    """Get story arc analysis for a script."""
    try:
        story_arc = get_story_arc_analysis(script_id)
        
        if not story_arc:
            return jsonify({
                'success': False,
                'error': 'No story arc analysis found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': story_arc
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/scripts/<int:script_id>/analysis/queue-character', methods=['POST'])
def queue_character_analysis(script_id):
    """Queue analysis for a specific character (priority processing)."""
    try:
        data = request.get_json() or {}
        character_name = data.get('character_name')
        
        if not character_name:
            return jsonify({
                'success': False,
                'error': 'character_name is required'
            }), 400
        
        # Ensure worker is running
        start_worker()
        
        # Create high-priority job for this character
        job_id = create_analysis_job(
            script_id,
            'character_detail',
            target_id=character_name,
            priority=1  # Highest priority
        )
        
        return jsonify({
            'success': True,
            'message': f'Queued priority analysis for {character_name}',
            'job_id': job_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/scripts/<int:script_id>/analysis/queue-location', methods=['POST'])
def queue_location_analysis(script_id):
    """Queue analysis for a specific location (priority processing)."""
    try:
        data = request.get_json() or {}
        location_name = data.get('location_name')
        
        if not location_name:
            return jsonify({
                'success': False,
                'error': 'location_name is required'
            }), 400
        
        # Ensure worker is running
        start_worker()
        
        # Create high-priority job for this location
        job_id = create_analysis_job(
            script_id,
            'location_detail',
            target_id=location_name,
            priority=1  # Highest priority
        )
        
        return jsonify({
            'success': True,
            'message': f'Queued priority analysis for {location_name}',
            'job_id': job_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
