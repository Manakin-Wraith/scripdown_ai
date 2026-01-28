"""
Feedback Routes - User feedback submission and management API endpoints
Handles bug reports, feature requests, UI/UX issues, and general feedback.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from middleware.auth import require_auth, get_user_id
from services.feedback_service import (
    submit_feedback,
    get_user_feedback,
    get_all_feedback,
    get_feedback_by_id,
    update_feedback_status,
    send_feedback_reply,
    delete_feedback,
    check_rate_limit,
    get_feedback_stats
)
from db.supabase_client import get_supabase_client

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')


@feedback_bp.route('', methods=['POST'])
@require_auth
def submit_feedback_route():
    """
    Submit new feedback.
    
    Request body:
        - category: 'bug', 'feature', 'ui_ux', or 'general' (required)
        - priority: 'low', 'medium', or 'high' (optional, default: 'medium')
        - subject: string, max 200 chars (required)
        - description: string, max 2000 chars (required)
        - screenshot: file (optional, max 5MB)
        - page_context: object with url, route, script_id, etc. (optional)
    
    Returns:
        201: Feedback submitted successfully
        400: Validation error
        429: Rate limit exceeded
    """
    try:
        user_id = get_user_id()
        
        # Check rate limit (5 submissions per day)
        if not check_rate_limit(user_id):
            return jsonify({
                'error': 'Rate limit exceeded. Maximum 5 feedback submissions per day.'
            }), 429
        
        # Get form data
        category = request.form.get('category')
        priority = request.form.get('priority', 'medium')
        subject = request.form.get('subject')
        description = request.form.get('description')
        page_context_str = request.form.get('page_context', '{}')
        
        # Validate required fields
        if not category or category not in ['bug', 'feature', 'ui_ux', 'general']:
            return jsonify({'error': 'Invalid category. Must be: bug, feature, ui_ux, or general'}), 400
        
        if not subject or len(subject) > 200:
            return jsonify({'error': 'Subject is required and must be 200 characters or less'}), 400
        
        if not description or len(description) > 2000:
            return jsonify({'error': 'Description is required and must be 2000 characters or less'}), 400
        
        if priority not in ['low', 'medium', 'high']:
            return jsonify({'error': 'Invalid priority. Must be: low, medium, or high'}), 400
        
        # Parse page context
        import json
        try:
            page_context = json.loads(page_context_str)
        except:
            page_context = {}
        
        # Handle screenshot upload
        screenshot_file = request.files.get('screenshot')
        
        # Submit feedback
        result = submit_feedback(
            user_id=user_id,
            category=category,
            priority=priority,
            subject=subject,
            description=description,
            screenshot_file=screenshot_file,
            page_context=page_context
        )
        
        if result.get('error'):
            return jsonify({'error': result['error']}), 400
        
        return jsonify({
            'id': result['id'],
            'message': 'Feedback submitted successfully',
            'screenshot_url': result.get('screenshot_url')
        }), 201
        
    except Exception as e:
        print(f"Error submitting feedback: {e}")
        return jsonify({'error': 'Failed to submit feedback'}), 500


@feedback_bp.route('', methods=['GET'])
@require_auth
def get_feedback_route():
    """
    Get feedback submissions.
    - Regular users: See only their own feedback
    - Superusers: See all feedback with filters
    
    Query params:
        - page: int (default: 1)
        - limit: int (default: 20, max: 100)
        - category: filter by category
        - status: filter by status
        - priority: filter by priority
        - search: search in subject/description
    
    Returns:
        200: List of feedback submissions
    """
    try:
        user_id = get_user_id()
        
        # Get query params
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        category = request.args.get('category')
        status = request.args.get('status')
        priority = request.args.get('priority')
        search = request.args.get('search')
        
        # Check if user is superuser
        supabase = get_supabase_client()
        profile = supabase.table('profiles').select('is_superuser').eq('id', user_id).single().execute()
        is_superuser = profile.data.get('is_superuser', False) if profile.data else False
        
        if is_superuser:
            # Superuser: Get all feedback with filters
            result = get_all_feedback(
                page=page,
                limit=limit,
                category=category,
                status=status,
                priority=priority,
                search=search
            )
        else:
            # Regular user: Get only their own feedback
            result = get_user_feedback(
                user_id=user_id,
                page=page,
                limit=limit
            )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error fetching feedback: {e}")
        return jsonify({'error': 'Failed to fetch feedback'}), 500


@feedback_bp.route('/<feedback_id>', methods=['GET'])
@require_auth
def get_feedback_detail_route(feedback_id):
    """
    Get single feedback submission by ID.
    Users can only view their own feedback unless they're superusers.
    
    Returns:
        200: Feedback details
        403: Forbidden
        404: Not found
    """
    try:
        user_id = get_user_id()
        
        result = get_feedback_by_id(feedback_id, user_id)
        
        if result.get('error'):
            status_code = 404 if 'not found' in result['error'].lower() else 403
            return jsonify({'error': result['error']}), status_code
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error fetching feedback detail: {e}")
        return jsonify({'error': 'Failed to fetch feedback'}), 500


@feedback_bp.route('/<feedback_id>/status', methods=['PATCH'])
@require_auth
def update_feedback_status_route(feedback_id):
    """
    Update feedback status (superuser only).
    
    Request body:
        - status: 'new', 'in_progress', 'resolved', or 'dismissed' (required)
        - admin_notes: string (optional)
    
    Returns:
        200: Status updated
        403: Forbidden (not superuser)
        404: Not found
    """
    try:
        user_id = get_user_id()
        
        # Check if user is superuser
        supabase = get_supabase_client()
        profile = supabase.table('profiles').select('is_superuser').eq('id', user_id).single().execute()
        is_superuser = profile.data.get('is_superuser', False) if profile.data else False
        
        if not is_superuser:
            return jsonify({'error': 'Forbidden. Superuser access required.'}), 403
        
        data = request.get_json()
        status = data.get('status')
        admin_notes = data.get('admin_notes')
        
        if not status or status not in ['new', 'in_progress', 'resolved', 'dismissed']:
            return jsonify({'error': 'Invalid status'}), 400
        
        result = update_feedback_status(
            feedback_id=feedback_id,
            status=status,
            admin_notes=admin_notes,
            resolved_by=user_id if status == 'resolved' else None
        )
        
        if result.get('error'):
            return jsonify({'error': result['error']}), 404
        
        return jsonify({
            'message': 'Status updated successfully',
            'feedback': result
        }), 200
        
    except Exception as e:
        print(f"Error updating feedback status: {e}")
        return jsonify({'error': 'Failed to update status'}), 500


@feedback_bp.route('/<feedback_id>/reply', methods=['POST'])
@require_auth
def send_feedback_reply_route(feedback_id):
    """
    Send email reply to feedback submitter (superuser only).
    
    Request body:
        - reply_message: string (required)
    
    Returns:
        200: Reply sent
        403: Forbidden
        404: Not found
    """
    try:
        user_id = get_user_id()
        
        # Check if user is superuser
        supabase = get_supabase_client()
        profile = supabase.table('profiles').select('is_superuser').eq('id', user_id).single().execute()
        is_superuser = profile.data.get('is_superuser', False) if profile.data else False
        
        if not is_superuser:
            return jsonify({'error': 'Forbidden. Superuser access required.'}), 403
        
        data = request.get_json()
        reply_message = data.get('reply_message')
        
        if not reply_message:
            return jsonify({'error': 'Reply message is required'}), 400
        
        result = send_feedback_reply(
            feedback_id=feedback_id,
            reply_message=reply_message,
            admin_user_id=user_id
        )
        
        if result.get('error'):
            return jsonify({'error': result['error']}), 404 if 'not found' in result['error'].lower() else 500
        
        return jsonify({
            'message': 'Reply sent successfully'
        }), 200
        
    except Exception as e:
        print(f"Error sending feedback reply: {e}")
        return jsonify({'error': 'Failed to send reply'}), 500


@feedback_bp.route('/<feedback_id>', methods=['DELETE'])
@require_auth
def delete_feedback_route(feedback_id):
    """
    Delete feedback submission (superuser only).
    
    Returns:
        200: Feedback deleted
        403: Forbidden
        404: Not found
    """
    try:
        user_id = get_user_id()
        
        result = delete_feedback(
            feedback_id=feedback_id,
            user_id=user_id
        )
        
        if result.get('error'):
            if 'Forbidden' in result['error']:
                return jsonify({'error': result['error']}), 403
            elif 'not found' in result['error'].lower():
                return jsonify({'error': result['error']}), 404
            else:
                return jsonify({'error': result['error']}), 500
        
        return jsonify({
            'message': 'Feedback deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"Error deleting feedback: {e}")
        return jsonify({'error': 'Failed to delete feedback'}), 500


@feedback_bp.route('/stats', methods=['GET'])
@require_auth
def get_feedback_stats_route():
    """
    Get feedback statistics (superuser only).
    
    Returns:
        200: Feedback stats
        403: Forbidden
    """
    try:
        user_id = get_user_id()
        
        # Check if user is superuser
        supabase = get_supabase_client()
        profile = supabase.table('profiles').select('is_superuser').eq('id', user_id).single().execute()
        is_superuser = profile.data.get('is_superuser', False) if profile.data else False
        
        if not is_superuser:
            return jsonify({'error': 'Forbidden. Superuser access required.'}), 403
        
        stats = get_feedback_stats()
        
        return jsonify(stats), 200
        
    except Exception as e:
        print(f"Error fetching feedback stats: {e}")
        return jsonify({'error': 'Failed to fetch stats'}), 500
