"""
Analysis API Routes - Endpoints for managing AI analysis jobs.

Endpoints:
- GET  /api/analysis/status - Get all scripts analysis status
- GET  /api/scripts/<id>/analysis/status - Get script analysis status
- POST /api/scripts/<id>/analysis/cancel - Cancel pending/processing jobs
- GET  /api/scripts/<id>/analysis/characters - Get all character analyses
- GET  /api/scripts/<id>/analysis/characters/<name> - Get specific character analysis
- GET  /api/scripts/<id>/analysis/story-arc - Get story arc analysis
"""

from flask import Blueprint, jsonify
from services.analysis_queue_service import (
    get_script_analysis_status,
    get_all_analysis_status,
    cancel_script_analysis,
    get_character_analysis,
    get_all_character_analyses,
    get_story_arc_analysis,
)

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


