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


@campaign_bp.route('/templates/<template_id>', methods=['PATCH'])
@require_auth
@require_superuser
def update_template(template_id):
    """
    Update an email template

    Body (all optional):
        name, subject, body_html, body_text, category, variables, is_active
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()

        data = request.get_json()

        existing = supabase.table('email_templates')\
            .select('id')\
            .eq('id', template_id)\
            .single()\
            .execute()

        if not existing.data:
            return jsonify({'success': False, 'error': 'Template not found'}), 404

        allowed = ['name', 'subject', 'body_html', 'body_text', 'category', 'variables', 'is_active']
        update_data = {k: data[k] for k in allowed if k in data}
        update_data['updated_at'] = datetime.now().isoformat()

        result = supabase.table('email_templates')\
            .update(update_data)\
            .eq('id', template_id)\
            .execute()

        return jsonify({
            'success': True,
            'template': result.data[0] if result.data else None
        }), 200

    except Exception as e:
        print(f"Error updating template: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@campaign_bp.route('/templates/<template_id>', methods=['DELETE'])
@require_auth
@require_superuser
def delete_template(template_id):
    """
    Delete an email template (hard delete).
    Soft-deactivate instead if you want to preserve history.
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()

        existing = supabase.table('email_templates')\
            .select('id')\
            .eq('id', template_id)\
            .single()\
            .execute()

        if not existing.data:
            return jsonify({'success': False, 'error': 'Template not found'}), 404

        supabase.table('email_templates')\
            .delete()\
            .eq('id', template_id)\
            .execute()

        return jsonify({'success': True, 'message': 'Template deleted'}), 200

    except Exception as e:
        print(f"Error deleting template: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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


@campaign_bp.route('/stats', methods=['GET'])
@require_auth
@require_superuser
def get_email_stats():
    """
    Get aggregated email statistics for the dashboard.
    Returns campaign totals, transactional email breakdown, template counts, audience stats.
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()

        # --- Campaign aggregate stats (from campaigns table for status/meta) ---
        campaigns_result = supabase.table('email_campaigns').select(
            'id, status, total_recipients, emails_sent, emails_failed, created_at, sent_at'
        ).execute()
        campaigns = campaigns_result.data or []

        total_campaigns = len(campaigns)
        total_recipients = sum(c.get('total_recipients') or 0 for c in campaigns)
        total_failed = sum(c.get('emails_failed') or 0 for c in campaigns)

        status_counts = {}
        for c in campaigns:
            s = c.get('status', 'unknown')
            status_counts[s] = status_counts.get(s, 0) + 1

        # --- Live recipient status counts (source of truth for rates) ---
        recipients_result = supabase.table('email_campaign_recipients').select(
            'status'
        ).execute()
        recipients = recipients_result.data or []

        live_sent      = sum(1 for r in recipients if r.get('status') in ('sent', 'delivered', 'opened', 'clicked'))
        live_delivered = sum(1 for r in recipients if r.get('status') in ('delivered', 'opened', 'clicked'))
        live_opened    = sum(1 for r in recipients if r.get('status') in ('opened', 'clicked'))
        live_clicked   = sum(1 for r in recipients if r.get('status') == 'clicked')
        live_bounced   = sum(1 for r in recipients if r.get('status') == 'bounced')

        # Use live counts; fall back to campaign aggregate for sent if live is 0
        total_sent      = live_sent or sum(c.get('emails_sent') or 0 for c in campaigns)
        total_delivered = live_delivered
        total_opened    = live_opened
        total_clicked   = live_clicked
        total_bounced   = live_bounced

        # --- Delivery / open / click rates ---
        delivery_rate = round((total_delivered / total_sent * 100) if total_sent > 0 else 0, 1)
        open_rate     = round((total_opened    / total_sent * 100) if total_sent > 0 else 0, 1)
        click_rate    = round((total_clicked   / total_sent * 100) if total_sent > 0 else 0, 1)

        # --- Transactional email breakdown from email_tracking ---
        tracking_result = supabase.table('email_tracking').select(
            'email_type, delivery_status, opened_at, clicked_at'
        ).execute()
        tracking_rows = tracking_result.data or []

        transactional_by_type = {}
        for row in tracking_rows:
            et = row.get('email_type', 'unknown')
            if et not in transactional_by_type:
                transactional_by_type[et] = {'total': 0, 'sent': 0, 'delivered': 0, 'failed': 0, 'opened': 0, 'clicked': 0}
            transactional_by_type[et]['total'] += 1
            ds = row.get('delivery_status', '')
            if ds in ('sent', 'delivered'):
                transactional_by_type[et]['sent'] += 1
            if ds == 'delivered':
                transactional_by_type[et]['delivered'] += 1
            if ds in ('failed', 'bounced'):
                transactional_by_type[et]['failed'] += 1
            if row.get('opened_at'):
                transactional_by_type[et]['opened'] += 1
            if row.get('clicked_at'):
                transactional_by_type[et]['clicked'] += 1

        transactional_total = len(tracking_rows)
        transactional_delivered = sum(1 for r in tracking_rows if r.get('delivery_status') == 'delivered')

        # --- Template counts ---
        templates_result = supabase.table('email_templates').select('id, category, is_active').execute()
        templates = templates_result.data or []
        template_counts = {'total': len(templates), 'active': sum(1 for t in templates if t.get('is_active'))}
        template_by_category = {}
        for t in templates:
            cat = t.get('category', 'other')
            template_by_category[cat] = template_by_category.get(cat, 0) + 1

        # --- Audience stats from profiles ---
        profiles_result = supabase.table('profiles').select('subscription_status').execute()
        profiles = profiles_result.data or []
        audience_by_status = {}
        for p in profiles:
            s = p.get('subscription_status', 'unknown')
            audience_by_status[s] = audience_by_status.get(s, 0) + 1

        return jsonify({
            'success': True,
            'campaigns': {
                'total': total_campaigns,
                'by_status': status_counts,
                'total_recipients': total_recipients,
                'emails_sent': total_sent,
                'emails_delivered': total_delivered,
                'emails_opened': total_opened,
                'emails_clicked': total_clicked,
                'emails_bounced': total_bounced,
                'emails_failed': total_failed,
                'delivery_rate': delivery_rate,
                'open_rate': open_rate,
                'click_rate': click_rate,
            },
            'transactional': {
                'total': transactional_total,
                'delivered': transactional_delivered,
                'by_type': transactional_by_type,
            },
            'templates': {
                'total': template_counts['total'],
                'active': template_counts['active'],
                'by_category': template_by_category,
            },
            'audience': {
                'total': len(profiles),
                'by_status': audience_by_status,
            }
        }), 200

    except Exception as e:
        print(f"Error getting email stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@campaign_bp.route('/transactional', methods=['GET'])
@require_auth
@require_superuser
def list_transactional_emails():
    """
    Paginated transactional email log from email_tracking.

    Query params:
        email_type: Filter by type (optional)
        delivery_status: Filter by status (optional)
        limit: Default 50
        offset: Default 0
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()

        email_type      = request.args.get('email_type')
        delivery_status = request.args.get('delivery_status')
        limit           = int(request.args.get('limit', 50))
        offset          = int(request.args.get('offset', 0))

        query = supabase.table('email_tracking')\
            .select(
                'id, email_type, recipient_email, recipient_name, delivery_status, '
                'resend_email_id, sent_at, opened_at, clicked_at, user_status, metadata',
                count='exact'
            )\
            .order('sent_at', desc=True)\
            .range(offset, offset + limit - 1)

        if email_type:
            query = query.eq('email_type', email_type)
        if delivery_status:
            query = query.eq('delivery_status', delivery_status)

        result = query.execute()

        return jsonify({
            'success': True,
            'emails': result.data or [],
            'total': result.count or 0,
            'limit': limit,
            'offset': offset,
        }), 200

    except Exception as e:
        print(f"Error listing transactional emails: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@campaign_bp.route('/audience/users', methods=['GET'])
@require_auth
@require_superuser
def list_audience_users():
    """
    Paginated list of users filtered by subscription_status.

    Query params:
        status: subscription_status value (optional — omit for all)
        limit: Default 50
        offset: Default 0
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()

        status = request.args.get('status')
        limit  = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        query = supabase.table('profiles')\
            .select(
                'id, full_name, email, subscription_status, trial_ends_at, created_at',
                count='exact'
            )\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)

        if status:
            query = query.eq('subscription_status', status)

        result = query.execute()

        return jsonify({
            'success': True,
            'users': result.data or [],
            'total': result.count or 0,
            'status_filter': status,
            'limit': limit,
            'offset': offset,
        }), 200

    except Exception as e:
        print(f"Error listing audience users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
