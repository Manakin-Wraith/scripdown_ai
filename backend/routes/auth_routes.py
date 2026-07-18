"""
Auth Routes - Authentication-related API endpoints
Handles welcome emails, signup plan assignment, and other auth-related functionality.
"""

from flask import Blueprint, request, jsonify
from services.email_service import send_welcome_email, send_feature_announcement_email, is_configured
from db.supabase_client import get_supabase_client
from middleware.auth import require_auth, get_user_id, get_current_user

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/welcome-email', methods=['POST'])
def send_welcome_email_route():
    """
    Send welcome email to a new user after signup.
    
    Request body:
        - email: User's email address
        - full_name: User's full name
    
    The endpoint checks if the user has already paid (beta_payments table)
    and sends the appropriate email variant.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        email = data.get('email')
        full_name = data.get('full_name', '')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Check if email service is configured
        if not is_configured():
            return jsonify({
                'error': 'Email service not configured',
                'sent': False
            }), 503
        
        # Check if user has already paid (beta_payments table)
        has_paid = False
        try:
            supabase = get_supabase_client()
            result = supabase.table('beta_payments') \
                .select('status') \
                .eq('email', email.lower().strip()) \
                .eq('status', 'completed') \
                .execute()
            
            has_paid = len(result.data) > 0
        except Exception as e:
            # If we can't check payment status, assume not paid
            print(f"Warning: Could not check payment status: {e}")
            has_paid = False
        
        # Send welcome email
        result = send_welcome_email(
            to_email=email,
            full_name=full_name,
            has_paid=has_paid
        )
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'sent': False
            }), 500
        
        return jsonify({
            'success': True,
            'sent': True,
            'has_paid': has_paid,
            'message': 'Welcome email sent successfully'
        })
        
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        return jsonify({
            'error': str(e),
            'sent': False
        }), 500


@auth_bp.route('/check-payment-status', methods=['POST'])
def check_payment_status():
    """
    Check if a user has paid for beta access.
    
    Request body:
        - email: User's email address
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Check beta_payments table
        supabase = get_supabase_client()
        result = supabase.table('beta_payments') \
            .select('*') \
            .eq('email', email.lower().strip()) \
            .eq('status', 'completed') \
            .execute()
        
        has_paid = len(result.data) > 0
        payment_data = result.data[0] if has_paid else None
        
        return jsonify({
            'has_paid': has_paid,
            'payment': payment_data
        })
        
    except Exception as e:
        print(f"Error checking payment status: {e}")
        return jsonify({
            'error': str(e),
            'has_paid': False
        }), 500


# Landing sends tier_1 / tier_2; the DB stores the full ids.
PLAN_ALIASES = {
    'tier_1': 'tier_1_pay_per_breakdown',
    'tier_2': 'tier_2_annual_team',
}
VALID_PLANS = {'tier_1_pay_per_breakdown', 'tier_2_annual_team'}


def _upsert_profile(user_id, data):
    from db.supabase_client import get_supabase_admin
    get_supabase_admin().table('profiles').upsert(
        {'id': user_id, **data}, on_conflict='id'
    ).execute()


@auth_bp.route('/set-plan', methods=['POST'])
@require_auth
def set_plan():
    """
    Record which plan a new signup intends to buy, and create their profile.

    This is the only thing that creates a profile row — no auth.users trigger
    does it — so email and full_name are written here.

    Identity comes from the verified token. A user_id or email in the body is
    ignored: honouring them allowed any caller to rewrite any user's plan.

    Setting a plan grants nothing. There is no free tier and no trial; only a
    confirmed PayFast payment (see routes/payfast_routes.py) grants access.
    """
    user_id = get_user_id()
    body = request.get_json(silent=True) or {}

    plan = body.get('plan')
    plan = PLAN_ALIASES.get(plan, plan)
    if plan not in VALID_PLANS:
        return jsonify({'error': f'Invalid plan: {body.get("plan")}'}), 400

    profile = {
        'signup_plan': plan,
        'signup_source': body.get('source', 'direct'),
        'subscription_status': 'none',   # no free tier — payment activates
        'subscription_plan': 'none',
        'updated_at': 'now()',
        # created_at deliberately NOT written: overwriting it reset account age.
    }

    # Email from the token, not the body, for the same reason as user_id.
    email = (get_current_user() or {}).get('email')
    if email:
        profile['email'] = email
    full_name = body.get('full_name')
    if full_name:
        profile['full_name'] = full_name

    try:
        _upsert_profile(user_id, profile)
    except Exception as e:
        print(f"Error setting plan for {user_id}: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

    return jsonify({'success': True, 'signup_plan': plan}), 200


@auth_bp.route('/send-feature-announcement', methods=['POST'])
def send_feature_announcement():
    """
    Send feature announcement email to specific users or all users.
    Admin endpoint for announcing new features.
    
    Request body:
        - recipients: List of email addresses (optional, sends to all if not provided)
        - features: List of feature dicts with 'icon', 'title', 'description' (optional)
        - send_to_all: Boolean to send to all active users (default: false)
    
    Returns:
        - success: bool
        - sent_count: int
        - failed_count: int
        - errors: list of error messages
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # Check if email service is configured
        if not is_configured():
            return jsonify({
                'error': 'Email service not configured',
                'success': False
            }), 503
        
        recipients = data.get('recipients', [])
        features = data.get('features')
        send_to_all = data.get('send_to_all', False)
        
        supabase = get_supabase_client()
        
        # If send_to_all is true, fetch all user emails from profiles
        if send_to_all:
            profiles_result = supabase.table('profiles') \
                .select('email, full_name') \
                .execute()
            
            recipients = [
                {'email': p['email'], 'full_name': p.get('full_name', '')}
                for p in profiles_result.data
            ]
        else:
            # If recipients is a list of emails, fetch their names
            if recipients and isinstance(recipients[0], str):
                profiles_result = supabase.table('profiles') \
                    .select('email, full_name') \
                    .in_('email', recipients) \
                    .execute()
                
                recipients = [
                    {'email': p['email'], 'full_name': p.get('full_name', '')}
                    for p in profiles_result.data
                ]
        
        if not recipients:
            return jsonify({
                'error': 'No recipients specified',
                'success': False
            }), 400
        
        # Send emails
        sent_count = 0
        failed_count = 0
        errors = []
        
        for recipient in recipients:
            try:
                result = send_feature_announcement_email(
                    to_email=recipient['email'],
                    full_name=recipient.get('full_name', ''),
                    features=features
                )
                
                if 'error' in result:
                    failed_count += 1
                    errors.append(f"{recipient['email']}: {result['error']}")
                else:
                    sent_count += 1
                    print(f"Feature announcement sent to {recipient['email']}")
            except Exception as e:
                failed_count += 1
                errors.append(f"{recipient['email']}: {str(e)}")
        
        return jsonify({
            'success': True,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_recipients': len(recipients),
            'errors': errors if errors else None
        })
        
    except Exception as e:
        print(f"Error sending feature announcements: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500
