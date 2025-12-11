"""
Auth Routes - Authentication-related API endpoints
Handles welcome emails and other auth-related functionality.
"""

from flask import Blueprint, request, jsonify
from services.email_service import send_welcome_email, is_configured
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
