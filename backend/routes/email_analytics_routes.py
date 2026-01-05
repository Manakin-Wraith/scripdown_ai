"""
Email Analytics Routes
Provides endpoints for viewing email tracking data and metrics.
"""

from flask import Blueprint, request, jsonify
from services.email_tracking_service import (
    get_email_analytics,
    get_recent_emails,
    check_if_email_sent
)
from middleware.auth import optional_auth

analytics_bp = Blueprint('email_analytics', __name__, url_prefix='/api/email-analytics')


@analytics_bp.route('/metrics', methods=['GET'])
@optional_auth
def get_metrics():
    """
    Get email metrics and analytics.
    
    Query params:
        - email_type: Filter by email type (optional)
        - start_date: Start date ISO string (optional)
        - end_date: End date ISO string (optional)
    
    Returns:
        {
            "metrics": {
                "total_sent": 100,
                "delivered": 95,
                "bounced": 5,
                "opened": 30,
                "clicked": 10,
                "delivery_rate": 95.0,
                "open_rate": 31.58,
                "click_rate": 10.53
            },
            "emails": [...]
        }
    """
    email_type = request.args.get('email_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    result = get_email_analytics(
        email_type=email_type,
        start_date=start_date,
        end_date=end_date
    )
    
    if not result.get('success'):
        return jsonify({'error': result.get('error')}), 500
    
    return jsonify({
        'metrics': result['metrics'],
        'total_emails': len(result['emails'])
    }), 200


@analytics_bp.route('/recent', methods=['GET'])
@optional_auth
def get_recent():
    """
    Get recent sent emails.
    
    Query params:
        - limit: Number of emails to retrieve (default: 50, max: 200)
    
    Returns:
        {
            "emails": [
                {
                    "id": "uuid",
                    "email_type": "beta_launch",
                    "recipient_email": "user@example.com",
                    "recipient_name": "John Doe",
                    "user_status": "new",
                    "resend_email_id": "abc123",
                    "sent_at": "2025-12-22T10:00:00Z",
                    "delivery_status": "delivered",
                    "opened_at": "2025-12-22T10:05:00Z",
                    "clicked_at": null,
                    "metadata": {...}
                },
                ...
            ],
            "count": 50
        }
    """
    limit = request.args.get('limit', 50, type=int)
    
    # Cap limit at 200
    if limit > 200:
        limit = 200
    
    emails = get_recent_emails(limit=limit)
    
    return jsonify({
        'emails': emails,
        'count': len(emails)
    }), 200


@analytics_bp.route('/check-sent', methods=['POST'])
@optional_auth
def check_sent():
    """
    Check if an email was already sent to a recipient.
    
    Request body:
        {
            "recipient_email": "user@example.com",
            "email_type": "beta_launch"
        }
    
    Returns:
        {
            "already_sent": true|false,
            "recipient_email": "user@example.com",
            "email_type": "beta_launch"
        }
    """
    data = request.get_json()
    
    recipient_email = data.get('recipient_email')
    email_type = data.get('email_type')
    
    if not recipient_email or not email_type:
        return jsonify({'error': 'recipient_email and email_type are required'}), 400
    
    already_sent = check_if_email_sent(recipient_email, email_type)
    
    return jsonify({
        'already_sent': already_sent,
        'recipient_email': recipient_email,
        'email_type': email_type
    }), 200


@analytics_bp.route('/summary', methods=['GET'])
@optional_auth
def get_summary():
    """
    Get a summary of all email campaigns.
    
    Returns:
        {
            "campaigns": [
                {
                    "email_type": "beta_launch",
                    "total_sent": 100,
                    "delivery_rate": 95.0,
                    "open_rate": 30.0,
                    "click_rate": 10.0
                },
                ...
            ]
        }
    """
    # Get all email types
    email_types = ['beta_launch', 'welcome', 'early_access', 'expiration_reminder', 'test']
    
    campaigns = []
    for email_type in email_types:
        result = get_email_analytics(email_type=email_type)
        
        if result.get('success') and result['metrics']['total_sent'] > 0:
            campaigns.append({
                'email_type': email_type,
                **result['metrics']
            })
    
    return jsonify({
        'campaigns': campaigns,
        'total_campaigns': len(campaigns)
    }), 200
