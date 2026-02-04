"""
Email Campaign Routes - API endpoints for campaign management
Superuser-only endpoints for creating and managing email campaigns
"""

from flask import Blueprint, jsonify, request
from middleware.auth import require_auth, require_superuser, get_user_id
from services.campaign_service import CampaignService
from datetime import datetime

campaign_bp = Blueprint('campaigns', __name__, url_prefix='/api/campaigns')

# Initialize campaign service
campaign_service = CampaignService()


# ============================================
# Template Management Endpoints
# ============================================

@campaign_bp.route('/templates', methods=['GET'])
@require_auth
@require_superuser
def list_templates():
    """
    Get all email templates
    
    Query params:
        category: Filter by category (optional)
        active_only: Only return active templates (default: true)
    
    Returns:
        JSON with template list
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        category = request.args.get('category')
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        query = supabase.table('email_templates').select('*')
        
        if category:
            query = query.eq('category', category)
        
        if active_only:
            query = query.eq('is_active', True)
        
        result = query.order('created_at', desc=True).execute()
        
        return jsonify({
            'success': True,
            'templates': result.data or [],
            'count': len(result.data or [])
        }), 200
        
    except Exception as e:
        print(f"Error listing templates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@campaign_bp.route('/templates/<template_id>', methods=['GET'])
@require_auth
@require_superuser
def get_template(template_id):
    """Get a specific template by ID"""
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        result = supabase.table('email_templates')\
            .select('*')\
            .eq('id', template_id)\
            .single()\
            .execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404
        
        return jsonify({
            'success': True,
            'template': result.data
        }), 200
        
    except Exception as e:
        print(f"Error getting template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@campaign_bp.route('/templates', methods=['POST'])
@require_auth
@require_superuser
def create_template():
    """
    Create a new email template
    
    Body:
        name: Template name (required)
        subject: Email subject (required)
        body_html: HTML content (required)
        body_text: Plain text version (optional)
        category: Template category (optional)
        variables: Array of variable names (optional)
    
    Returns:
        Created template
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        data = request.get_json()
        user_id = get_user_id()
        
        # Validate required fields
        if not data.get('name') or not data.get('subject') or not data.get('body_html'):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, subject, body_html'
            }), 400
        
        template_data = {
            'name': data['name'],
            'subject': data['subject'],
            'body_html': data['body_html'],
            'body_text': data.get('body_text'),
            'category': data.get('category', 'marketing'),
            'variables': data.get('variables', []),
            'created_by': user_id
        }
        
        result = supabase.table('email_templates')\
            .insert(template_data)\
            .execute()
        
        return jsonify({
            'success': True,
            'template': result.data[0] if result.data else None
        }), 201
        
    except Exception as e:
        print(f"Error creating template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# Campaign Management Endpoints
# ============================================

@campaign_bp.route('/', methods=['GET'])
@require_auth
@require_superuser
def list_campaigns():
    """
    List all campaigns with optional filtering
    
    Query params:
        status: Filter by status (draft, scheduled, sending, sent, paused, cancelled)
        limit: Maximum records (default: 50)
        offset: Pagination offset (default: 0)
    
    Returns:
        JSON with campaign list
    """
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        result = campaign_service.list_campaigns(
            status=status,
            limit=limit,
            offset=offset
        )
        
        return jsonify(result), 200 if result['success'] else 500
        
    except Exception as e:
        print(f"Error listing campaigns: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@campaign_bp.route('/', methods=['POST'])
@require_auth
@require_superuser
def create_campaign():
    """
    Create a new campaign
    
    Body:
        name: Campaign name (required)
        description: Campaign description (optional)
        template_id: Template UUID (required)
        audience_filter: Audience segmentation filters (optional if manual_recipients provided)
        manual_recipients: Comma/newline-separated email addresses (optional)
        scheduled_at: ISO timestamp for scheduled send (optional)
    
    Returns:
        Created campaign with recipient count
    """
    try:
        data = request.get_json()
        user_id = get_user_id()
        
        # Validate required fields
        if not data.get('name') or not data.get('template_id'):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, template_id'
            }), 400
        
        # Either audience_filter or manual_recipients must be provided
        if not data.get('audience_filter') and not data.get('manual_recipients'):
            return jsonify({
                'success': False,
                'error': 'Either audience_filter or manual_recipients must be provided'
            }), 400
        
        result = campaign_service.create_campaign(
            name=data['name'],
            description=data.get('description', ''),
            template_id=data['template_id'],
            audience_filter=data.get('audience_filter', {}),
            created_by=user_id,
            scheduled_at=data.get('scheduled_at'),
            manual_recipients=data.get('manual_recipients'),
            template_variables=data.get('template_variables', {})
        )
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        print(f"Error creating campaign: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@campaign_bp.route('/<campaign_id>', methods=['GET'])
@require_auth
@require_superuser
def get_campaign(campaign_id):
    """Get campaign details including recipients"""
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Get campaign
        campaign_result = supabase.table('email_campaigns')\
            .select('*, email_templates(name, subject)')\
            .eq('id', campaign_id)\
            .single()\
            .execute()
        
        if not campaign_result.data:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        # Get recipients summary
        recipients_result = supabase.table('email_campaign_recipients')\
            .select('status', count='exact')\
            .eq('campaign_id', campaign_id)\
            .execute()
        
        # Count by status
        status_counts = {}
        for recipient in recipients_result.data or []:
            status = recipient['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return jsonify({
            'success': True,
            'campaign': campaign_result.data,
            'recipient_status_counts': status_counts
        }), 200
        
    except Exception as e:
        print(f"Error getting campaign: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@campaign_bp.route('/<campaign_id>/send', methods=['POST'])
@require_auth
@require_superuser
def send_campaign(campaign_id):
    """
    Send campaign immediately
    
    Returns:
        Updated campaign data
    """
    try:
        result = campaign_service.send_campaign(campaign_id)
        
        if result['success']:
            # TODO: Trigger background job to send emails
            # For now, just update status
            pass
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        print(f"Error sending campaign: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@campaign_bp.route('/<campaign_id>/analytics', methods=['GET'])
@require_auth
@require_superuser
def get_campaign_analytics(campaign_id):
    """
    Get campaign analytics
    
    Returns:
        Campaign performance metrics
    """
    try:
        result = campaign_service.get_campaign_analytics(campaign_id)
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        print(f"Error getting campaign analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@campaign_bp.route('/preview', methods=['POST'])
@require_auth
@require_superuser
def preview_audience():
    """
    Preview audience for campaign without creating it
    
    Body:
        audience_filter: Audience segmentation filters
    
    Returns:
        Audience statistics and sample users
    """
    try:
        data = request.get_json()
        
        if not data.get('audience_filter'):
            return jsonify({
                'success': False,
                'error': 'Missing audience_filter'
            }), 400
        
        result = campaign_service.get_campaign_preview(data['audience_filter'])
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        print(f"Error previewing audience: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@campaign_bp.route('/<campaign_id>', methods=['PATCH'])
@require_auth
@require_superuser
def update_campaign(campaign_id):
    """
    Update campaign (only draft campaigns can be updated)
    
    Body:
        name: Campaign name (optional)
        description: Campaign description (optional)
        scheduled_at: ISO timestamp (optional)
        status: Campaign status (optional)
    
    Returns:
        Updated campaign
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        data = request.get_json()
        
        # Check campaign exists and is draft
        campaign_result = supabase.table('email_campaigns')\
            .select('status')\
            .eq('id', campaign_id)\
            .single()\
            .execute()
        
        if not campaign_result.data:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        # Only allow updates to draft or scheduled campaigns
        if campaign_result.data['status'] not in ['draft', 'scheduled']:
            return jsonify({
                'success': False,
                'error': 'Can only update draft or scheduled campaigns'
            }), 400
        
        # Build update data
        update_data = {
            'updated_at': datetime.now().isoformat()
        }
        
        if 'name' in data:
            update_data['name'] = data['name']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'scheduled_at' in data:
            update_data['scheduled_at'] = data['scheduled_at']
        if 'status' in data:
            update_data['status'] = data['status']
        
        result = supabase.table('email_campaigns')\
            .update(update_data)\
            .eq('id', campaign_id)\
            .execute()
        
        return jsonify({
            'success': True,
            'campaign': result.data[0] if result.data else None
        }), 200
        
    except Exception as e:
        print(f"Error updating campaign: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@campaign_bp.route('/<campaign_id>', methods=['DELETE'])
@require_auth
@require_superuser
def delete_campaign(campaign_id):
    """
    Delete campaign (superusers can delete any campaign)
    
    Returns:
        Success status
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        # Check campaign exists
        campaign_result = supabase.table('email_campaigns')\
            .select('id, status')\
            .eq('id', campaign_id)\
            .single()\
            .execute()
        
        if not campaign_result.data:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        # Superusers can delete campaigns in any status
        # Delete campaign (recipients will cascade delete)
        supabase.table('email_campaigns')\
            .delete()\
            .eq('id', campaign_id)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': 'Campaign deleted'
        }), 200
        
    except Exception as e:
        print(f"Error deleting campaign: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# Recipient Management Endpoints
# ============================================

@campaign_bp.route('/<campaign_id>/recipients', methods=['GET'])
@require_auth
@require_superuser
def get_campaign_recipients(campaign_id):
    """
    Get recipients for a campaign
    
    Query params:
        status: Filter by status (optional)
        limit: Maximum records (default: 100)
        offset: Pagination offset (default: 0)
    
    Returns:
        List of recipients with their status
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        query = supabase.table('email_campaign_recipients')\
            .select('*', count='exact')\
            .eq('campaign_id', campaign_id)\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)
        
        if status:
            query = query.eq('status', status)
        
        result = query.execute()
        
        return jsonify({
            'success': True,
            'recipients': result.data or [],
            'total': result.count or 0,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        print(f"Error getting recipients: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
