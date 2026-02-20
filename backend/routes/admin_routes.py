"""
Admin Routes - Superuser-only endpoints for analytics and system management
"""

from flask import Blueprint, jsonify, request
from middleware.auth import require_auth, require_superuser
from services.analytics_service import AnalyticsService

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Initialize analytics service
analytics_service = AnalyticsService()


# ============================================
# Analytics Endpoints
# ============================================

@admin_bp.route('/analytics/overview', methods=['GET'])
@require_auth
@require_superuser
def get_analytics_overview():
    """
    Get high-level analytics overview
    
    Returns:
        JSON with global stats, user activity summary, and system health
    """
    try:
        global_stats = analytics_service.get_global_stats()
        subscription_metrics = analytics_service.get_subscription_metrics()
        
        return jsonify({
            'success': True,
            'data': {
                'global_stats': global_stats,
                'subscription_metrics': subscription_metrics
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/users', methods=['GET'])
@require_auth
@require_superuser
def get_user_activity():
    """Get user activity analytics with pagination and filtering"""
    try:
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status', None, type=str)
        search = request.args.get('search', None, type=str)
        
        analytics = AnalyticsService()
        result = analytics.get_user_activity(
            days=days, 
            limit=limit, 
            offset=offset,
            status_filter=status,
            search=search
        )
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        print(f"Error in get_user_activity: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/charts', methods=['GET'])
@require_auth
@require_superuser
def get_chart_data():
    """Get chart data for visualizations"""
    try:
        days = request.args.get('days', 30, type=int)
        
        analytics = AnalyticsService()
        chart_data = analytics.get_chart_data(days=days)
        
        return jsonify({
            'success': True,
            'data': chart_data
        }), 200
        
    except Exception as e:
        print(f"Error in get_chart_data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/activity', methods=['GET'])
@require_auth
@require_superuser
def get_recent_activity():
    """Get recent platform activity feed"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        analytics = AnalyticsService()
        activities = analytics.get_recent_activity(limit=limit)
        
        return jsonify({
            'success': True,
            'data': activities,
            'count': len(activities)
        }), 200
        
    except Exception as e:
        print(f"Error in get_recent_activity: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/scripts', methods=['GET'])
@require_auth
@require_superuser
def get_script_analytics_endpoint():
    """Get comprehensive script analytics and performance metrics"""
    try:
        analytics = AnalyticsService()
        script_data = analytics.get_script_analytics()
        
        return jsonify({
            'success': True,
            'data': script_data
        }), 200
        
    except Exception as e:
        print(f"Error in get_script_analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/scripts/stats', methods=['GET'])
@require_auth
@require_superuser
def get_script_stats_endpoint():
    """
    Get script analysis statistics
    
    Query params:
        days: Number of days to look back (default: 30)
    
    Returns:
        JSON with script stats
    """
    try:
        days = int(request.args.get('days', 30))
        
        script_stats = analytics_service.get_script_stats(days=days)
        
        return jsonify({
            'success': True,
            'data': script_stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/performance', methods=['GET'])
@require_auth
@require_superuser
def get_performance_analytics():
    """
    Get system performance metrics
    
    Returns:
        JSON with performance data including job stats and error rates
    """
    try:
        performance_metrics = analytics_service.get_performance_metrics()
        
        return jsonify({
            'success': True,
            'data': performance_metrics
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/subscriptions', methods=['GET'])
@require_auth
@require_superuser
def get_subscription_analytics():
    """
    Get subscription and conversion metrics
    
    Returns:
        JSON with subscription stats
    """
    try:
        subscription_metrics = analytics_service.get_subscription_metrics()
        
        return jsonify({
            'success': True,
            'data': subscription_metrics
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/analytics/revenue/details', methods=['GET'])
@require_auth
@require_superuser
def get_revenue_details():
    """
    Get detailed revenue breakdown with filters
    
    Query params:
        start_date: Start date filter (ISO format)
        end_date: End date filter (ISO format)
        search: Search by email
        sort_by: Column to sort by (default: created_at)
        sort_order: Sort direction (asc/desc, default: desc)
    
    Returns:
        JSON with revenue details, summary stats, and payment list
    """
    try:
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        search = request.args.get('search', None)
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        revenue_details = analytics_service.get_revenue_details(
            start_date=start_date,
            end_date=end_date,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        print(f"[revenue/details] payments sample: {[{'email': p.get('email'), 'package_type': p.get('package_type')} for p in (revenue_details.get('payments') or [])[:5]]}")
        return jsonify(revenue_details), 200
        
    except Exception as e:
        print(f"Error in get_revenue_details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# User Management Endpoints
# ============================================

@admin_bp.route('/users', methods=['GET'])
@require_auth
@require_superuser
def list_users():
    """
    List all users with filtering options
    
    Query params:
        status: Filter by subscription_status (trial, active, expired)
        limit: Maximum records (default: 50)
        offset: Pagination offset (default: 0)
    
    Returns:
        JSON with user list
    """
    try:
        from db.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status = request.args.get('status')
        
        query = supabase.table('profiles')\
            .select('id, full_name, email, subscription_status, trial_ends_at, created_at')\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)
        
        if status:
            query = query.eq('subscription_status', status)
        
        result = query.execute()
        
        return jsonify({
            'success': True,
            'data': result.data,
            'count': len(result.data)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/users/<user_id>', methods=['GET'])
@require_auth
@require_superuser
def get_user_details(user_id):
    """
    Get detailed information about a specific user
    
    Returns:
        JSON with user details including scripts and activity
    """
    try:
        from db.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Get user profile
        user_result = supabase.table('profiles')\
            .select('*')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        if not user_result.data:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Get user's scripts — use correct column names
        scripts_result = supabase.table('scripts')\
            .select('id, title, created_at, analysis_status, total_pages')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .execute()
        
        return jsonify({
            'success': True,
            'data': {
                'profile': user_result.data,
                'scripts': scripts_result.data,
                'script_count': len(scripts_result.data)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# Payment Verification Endpoints
# ============================================

@admin_bp.route('/payments/pending', methods=['GET'])
@require_auth
@require_superuser
def get_pending_payments():
    """
    Get all pending payments awaiting verification.
    Merges two sources:
      1. script_credit_purchases (status=pending) — in-app credit pack purchases
      2. beta_payments (status=pending) — landing_hero Yoco paylink signups
    
    Returns:
        JSON with list of pending purchases
    """
    try:
        from db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()
        
        # 1. Pending in-app credit purchases
        credit_result = supabase.table('script_credit_purchases')\
            .select('id, user_id, email, package_type, credits_purchased, amount, created_at, payment_reference, yoco_payment_id')\
            .eq('status', 'pending')\
            .order('created_at', desc=False)\
            .execute()
        
        credit_payments = credit_result.data or []
        
        # 2. Pending beta_payments (landing_hero signups awaiting Yoco verification)
        beta_result = supabase.table('beta_payments')\
            .select('id, user_id, email, amount, currency, created_at, payment_reference, metadata')\
            .eq('status', 'pending')\
            .order('created_at', desc=False)\
            .execute()
        
        # Normalise beta_payments rows to match the credit_purchases shape
        beta_payments = []
        for bp in (beta_result.data or []):
            beta_payments.append({
                'id': bp['id'],
                'user_id': bp.get('user_id'),
                'email': bp.get('email'),
                'package_type': 'beta_access',
                'credits_purchased': None,
                'amount': float(bp.get('amount', 249)),
                'created_at': bp.get('created_at'),
                'payment_reference': bp.get('payment_reference'),
                'yoco_payment_id': None,
                'payment_type': 'beta_access',
                'metadata': bp.get('metadata', {})
            })
        
        # Tag credit purchases with their type for the UI
        for cp in credit_payments:
            cp['payment_type'] = 'credit_purchase'
        
        all_pending = beta_payments + credit_payments
        all_pending.sort(key=lambda x: x.get('created_at') or '')
        
        return jsonify({
            'success': True,
            'data': all_pending,
            'count': len(all_pending)
        }), 200
        
    except Exception as e:
        print(f"Error getting pending payments: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/payments/<purchase_id>/approve', methods=['POST'])
@require_auth
@require_superuser
def approve_payment(purchase_id):
    """
    Approve a pending payment.
    Handles two payment types:
      - beta_access: marks beta_payments as completed, activates subscription
      - credit_purchase: marks script_credit_purchases as completed, adds credits
    
    Body:
        admin_reference: Optional Yoco reference number
        notes: Optional verification notes
        payment_type: 'beta_access' or 'credit_purchase' (optional, auto-detected)
    
    Returns:
        JSON with success status
    """
    try:
        from db.supabase_client import get_supabase_admin
        from middleware.auth import get_user_id
        from datetime import datetime, timedelta
        
        data = request.get_json() or {}
        admin_reference = data.get('admin_reference')
        notes = data.get('notes')
        payment_type = data.get('payment_type')
        admin_user_id = get_user_id()
        
        supabase = get_supabase_admin()
        
        # Auto-detect payment type if not provided: check beta_payments first
        if not payment_type:
            beta_check = supabase.table('beta_payments') \
                .select('id') \
                .eq('id', purchase_id) \
                .execute()
            payment_type = 'beta_access' if beta_check.data else 'credit_purchase'
        
        if payment_type == 'beta_access':
            # Fetch beta_payment record
            bp_result = supabase.table('beta_payments') \
                .select('*') \
                .eq('id', purchase_id) \
                .single() \
                .execute()
            
            if not bp_result.data:
                return jsonify({'success': False, 'error': 'Beta payment record not found'}), 404
            
            bp = bp_result.data
            user_id = bp.get('user_id')
            
            # Mark beta_payment as completed
            supabase.table('beta_payments').update({
                'status': 'completed',
                'payment_reference': admin_reference or bp.get('payment_reference'),
                'paid_at': datetime.now().isoformat(),
                'metadata': {**(bp.get('metadata') or {}), 'verified_by': admin_user_id, 'notes': notes}
            }).eq('id', purchase_id).execute()
            
            # Activate subscription on the user's profile (6 months)
            if user_id:
                expires_at = datetime.now() + timedelta(days=180)
                supabase.table('profiles').update({
                    'subscription_status': 'active',
                    'subscription_expires_at': expires_at.isoformat()
                }).eq('id', user_id).execute()
            
            return jsonify({
                'success': True,
                'message': 'Beta access activated — subscription set to active for 6 months'
            }), 200
        
        else:
            # credit_purchase path
            from services.credit_service import complete_credit_purchase
            
            result = complete_credit_purchase(purchase_id, admin_reference)
            
            if result['success']:
                supabase.table('script_credit_purchases').update({
                    'verified_by': admin_user_id,
                    'verified_at': datetime.now().isoformat(),
                    'verification_notes': notes,
                    'admin_reference': admin_reference
                }).eq('id', purchase_id).execute()
                
                return jsonify({
                    'success': True,
                    'message': f"{result['credits_added']} credits added to user account"
                }), 200
            else:
                return jsonify({'success': False, 'error': result['error']}), 400
            
    except Exception as e:
        print(f"Error approving payment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/payments/<purchase_id>/reject', methods=['POST'])
@require_auth
@require_superuser
def reject_payment(purchase_id):
    """
    Reject a pending payment.
    Handles both beta_payments and script_credit_purchases.
    
    Body:
        reason: Reason for rejection
        payment_type: 'beta_access' or 'credit_purchase' (optional, auto-detected)
    
    Returns:
        JSON with success status
    """
    try:
        from db.supabase_client import get_supabase_admin
        from middleware.auth import get_user_id
        from datetime import datetime
        
        data = request.get_json() or {}
        reason = data.get('reason', 'Payment verification failed')
        payment_type = data.get('payment_type')
        admin_user_id = get_user_id()
        
        supabase = get_supabase_admin()
        
        # Auto-detect payment type
        if not payment_type:
            beta_check = supabase.table('beta_payments') \
                .select('id') \
                .eq('id', purchase_id) \
                .execute()
            payment_type = 'beta_access' if beta_check.data else 'credit_purchase'
        
        if payment_type == 'beta_access':
            supabase.table('beta_payments').update({
                'status': 'failed',
                'metadata': {'rejected_by': admin_user_id, 'reason': reason, 'rejected_at': datetime.now().isoformat()}
            }).eq('id', purchase_id).execute()
        else:
            supabase.table('script_credit_purchases').update({
                'status': 'failed',
                'verified_by': admin_user_id,
                'verified_at': datetime.now().isoformat(),
                'verification_notes': reason
            }).eq('id', purchase_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Payment rejected'
        }), 200
        
    except Exception as e:
        print(f"Error rejecting payment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# System Health Endpoints
# ============================================

@admin_bp.route('/health', methods=['GET'])
@require_auth
@require_superuser
def get_system_health():
    """
    Get system health status
    
    Returns:
        JSON with system health indicators
    """
    try:
        from db.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Check database connectivity
        db_healthy = True
        try:
            supabase.table('profiles').select('id').limit(1).execute()
        except:
            db_healthy = False
        
        # Check for stuck jobs
        stuck_jobs_result = supabase.table('analysis_jobs')\
            .select('job_id', count='exact')\
            .eq('status', 'processing')\
            .execute()
        
        stuck_jobs = stuck_jobs_result.count or 0
        
        # Check for recent failures
        from datetime import datetime, timedelta
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        recent_failures = supabase.table('analysis_jobs')\
            .select('job_id', count='exact')\
            .eq('status', 'failed')\
            .gte('created_at', one_hour_ago)\
            .execute()
        
        return jsonify({
            'success': True,
            'data': {
                'database': 'healthy' if db_healthy else 'unhealthy',
                'stuck_jobs': stuck_jobs,
                'recent_failures': recent_failures.count or 0,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
