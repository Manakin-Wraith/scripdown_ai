"""
Auth Routes - Authentication-related API endpoints
Handles welcome emails, subscription status, and other auth-related functionality.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from services.email_service import send_welcome_email, is_configured
from services.subscription_service import (
    get_subscription_status, 
    can_upload_script,
    EARLY_ACCESS_TRIAL_DAYS,
    TRIAL_DURATION_DAYS
)
from db.supabase_client import get_supabase_client

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


@auth_bp.route('/subscription-status', methods=['POST'])
def get_subscription_status_route():
    """
    Get subscription status for a user.
    
    Request body:
        - user_id: User's UUID
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        status = get_subscription_status(user_id)
        return jsonify(status)
        
    except Exception as e:
        print(f"Error getting subscription status: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/can-upload-script', methods=['POST'])
def can_upload_script_route():
    """
    Check if user can upload a new script.
    
    Request body:
        - user_id: User's UUID
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        can_upload, message = can_upload_script(user_id)
        
        return jsonify({
            'can_upload': can_upload,
            'message': message,
            'upgrade_url': 'https://pay.yoco.com/r/2JB0rQ' if not can_upload else None
        })
        
    except Exception as e:
        print(f"Error checking upload permission: {e}")
        return jsonify({
            'error': str(e),
            'can_upload': False
        }), 500


@auth_bp.route('/apply-early-access', methods=['POST'])
def apply_early_access():
    """
    Check if user is an early access user and apply extended trial.
    Called after signup/profile creation to upgrade trial from 14 to 30 days.
    
    Request body:
        - email: User's email address
        - user_id: User's UUID (optional, for linking)
    
    Returns:
        - is_early_access: bool
        - trial_days: int (30 for early access, 14 for regular)
        - message: str
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        email = data.get('email')
        user_id = data.get('user_id')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        supabase = get_supabase_client()
        
        # Check if email is in early_access_users table
        result = supabase.table('early_access_users') \
            .select('*') \
            .eq('email', email.lower().strip()) \
            .eq('status', 'invited') \
            .execute()
        
        if not result.data or len(result.data) == 0:
            # Not an early access user - regular 14-day trial
            return jsonify({
                'is_early_access': False,
                'trial_days': TRIAL_DURATION_DAYS,
                'message': 'Regular trial access'
            })
        
        early_access = result.data[0]
        trial_days = early_access.get('trial_days', EARLY_ACCESS_TRIAL_DAYS)
        
        # Calculate trial expiry date
        trial_expires_at = datetime.now() + timedelta(days=trial_days)
        
        # Update the user's profile with extended trial
        if user_id:
            supabase.table('profiles') \
                .update({
                    'subscription_status': 'trial',
                    'subscription_expires_at': trial_expires_at.isoformat()
                }) \
                .eq('id', user_id) \
                .execute()
            
            # Mark early access user as signed up
            supabase.table('early_access_users') \
                .update({
                    'status': 'signed_up',
                    'user_id': user_id,
                    'signed_up_at': datetime.now().isoformat()
                }) \
                .eq('email', email.lower().strip()) \
                .execute()
            
            print(f"Applied early access trial ({trial_days} days) for {email}")
        
        return jsonify({
            'is_early_access': True,
            'trial_days': trial_days,
            'trial_expires_at': trial_expires_at.isoformat(),
            'message': f'Early access! You have {trial_days} days free trial'
        })
        
    except Exception as e:
        print(f"Error applying early access: {e}")
        return jsonify({
            'error': str(e),
            'is_early_access': False
        }), 500
