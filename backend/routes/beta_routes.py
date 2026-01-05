"""
Beta Launch Email Routes
Handles sending beta launch invitation emails to users.
"""

from flask import Blueprint, request, jsonify
from services.email_service import send_welcome_email, is_configured
from services.email_tracking_service import log_email_sent, get_email_analytics, get_recent_emails, check_if_email_sent
from middleware.auth import optional_auth, get_user_id
from db.supabase_client import SupabaseDB

beta_bp = Blueprint('beta', __name__, url_prefix='/api/beta')
db = SupabaseDB()


@beta_bp.route('/send-launch-email', methods=['POST'])
@optional_auth
def send_launch_email():
    """
    Send beta launch email to a user.
    
    Request body:
        {
            "email": "user@example.com",
            "full_name": "John Doe",
            "user_status": "new|trial|waitlist"  (optional, defaults to 'new')
        }
    
    Returns:
        {
            "message": "Email sent successfully",
            "email_id": "resend_email_id"
        }
    """
    if not is_configured():
        return jsonify({'error': 'Email service not configured'}), 500
    
    data = request.get_json()
    
    # Validate required fields
    email = data.get('email')
    full_name = data.get('full_name')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    if not full_name:
        return jsonify({'error': 'Full name is required'}), 400
    
    # Get optional user status
    user_status = data.get('user_status', 'new')
    
    # Validate user status
    if user_status not in ['new', 'trial', 'waitlist']:
        return jsonify({'error': 'Invalid user_status. Must be: new, trial, or waitlist'}), 400
    
    # Send email
    result = send_welcome_email(
        to_email=email,
        full_name=full_name,
        has_paid=False
    )
    
    # Check for errors
    if 'error' in result:
        return jsonify({'error': result['error']}), 500
    
    # Log email to database for tracking
    log_email_sent(
        email_type='beta_launch',
        recipient_email=email,
        recipient_name=full_name,
        resend_email_id=result.get('id'),
        user_status=user_status,
        metadata={'source': 'manual_send'}
    )
    
    return jsonify({
        'message': 'Beta launch email sent successfully',
        'email_id': result.get('id')
    }), 200


@beta_bp.route('/send-bulk-launch-emails', methods=['POST'])
@optional_auth
def send_bulk_launch_emails():
    """
    Send beta launch emails to multiple users.
    
    Request body:
        {
            "users": [
                {
                    "email": "user1@example.com",
                    "full_name": "John Doe",
                    "user_status": "new"
                },
                {
                    "email": "user2@example.com",
                    "full_name": "Jane Smith",
                    "user_status": "trial"
                }
            ]
        }
    
    Returns:
        {
            "message": "Emails sent",
            "sent": 2,
            "failed": 0,
            "results": [...]
        }
    """
    if not is_configured():
        return jsonify({'error': 'Email service not configured'}), 500
    
    data = request.get_json()
    users = data.get('users', [])
    
    if not users or not isinstance(users, list):
        return jsonify({'error': 'users array is required'}), 400
    
    results = []
    sent_count = 0
    failed_count = 0
    
    for user in users:
        email = user.get('email')
        full_name = user.get('full_name')
        user_status = user.get('user_status', 'new')
        
        # Skip invalid entries
        if not email or not full_name:
            results.append({
                'email': email,
                'status': 'failed',
                'error': 'Missing email or full_name'
            })
            failed_count += 1
            continue
        
        # Validate user status
        if user_status not in ['new', 'trial', 'waitlist']:
            results.append({
                'email': email,
                'status': 'failed',
                'error': 'Invalid user_status'
            })
            failed_count += 1
            continue
        
        # Send email
        result = send_welcome_email(
            to_email=email,
            full_name=full_name,
            has_paid=False
        )
        
        if 'error' in result:
            results.append({
                'email': email,
                'status': 'failed',
                'error': result['error']
            })
            failed_count += 1
        else:
            # Log successful send
            log_email_sent(
                email_type='beta_launch',
                recipient_email=email,
                recipient_name=full_name,
                resend_email_id=result.get('id'),
                user_status=user_status,
                metadata={'source': 'bulk_send'}
            )
            
            results.append({
                'email': email,
                'status': 'sent',
                'email_id': result.get('id')
            })
            sent_count += 1
    
    return jsonify({
        'message': f'Bulk email send complete',
        'sent': sent_count,
        'failed': failed_count,
        'total': len(users),
        'results': results
    }), 200


@beta_bp.route('/track-referral', methods=['POST'])
@optional_auth
def track_referral():
    """
    Track a manual referral submission.
    
    Request body:
        {
            "referrer_email": "referrer@example.com",
            "referred_emails": ["friend1@example.com", "friend2@example.com", "friend3@example.com"]
        }
    
    Returns:
        {
            "message": "Referral tracked",
            "referrer_email": "referrer@example.com",
            "referred_count": 3
        }
    """
    data = request.get_json()
    
    referrer_email = data.get('referrer_email')
    referred_emails = data.get('referred_emails', [])
    
    if not referrer_email:
        return jsonify({'error': 'referrer_email is required'}), 400
    
    if not referred_emails or not isinstance(referred_emails, list):
        return jsonify({'error': 'referred_emails array is required'}), 400
    
    # TODO: Store in database when referral system is implemented
    # For now, just log it
    print(f"📧 Referral tracked: {referrer_email} referred {len(referred_emails)} friends")
    print(f"   Referred emails: {', '.join(referred_emails)}")
    
    return jsonify({
        'message': 'Referral tracked successfully',
        'referrer_email': referrer_email,
        'referred_count': len(referred_emails),
        'note': 'Manual verification required. Email beta@slateone.studio to claim reward.'
    }), 200
