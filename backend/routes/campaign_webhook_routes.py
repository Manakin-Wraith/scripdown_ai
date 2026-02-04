"""
Campaign Webhook Routes
Handles webhooks from Resend for email tracking events
"""

from flask import Blueprint, request, jsonify
from db.supabase_client import get_supabase_admin
from datetime import datetime
import hmac
import hashlib

webhook_bp = Blueprint('campaign_webhooks', __name__, url_prefix='/api/campaigns/webhooks')


def verify_resend_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Resend webhook signature
    
    Args:
        payload: Raw request body
        signature: Signature from Resend-Signature header
        secret: Webhook signing secret from Resend dashboard
    
    Returns:
        True if signature is valid
    """
    if not secret:
        return True  # Skip verification if no secret configured
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


@webhook_bp.route('/resend', methods=['POST'])
def resend_webhook():
    """
    Handle Resend webhook events for email tracking
    
    Events:
    - email.sent: Email was sent
    - email.delivered: Email was delivered to inbox
    - email.delivery_delayed: Delivery delayed
    - email.bounced: Email bounced
    - email.opened: Email was opened
    - email.clicked: Link in email was clicked
    - email.complained: Marked as spam
    """
    try:
        # Get raw payload for signature verification
        payload = request.get_data()
        signature = request.headers.get('Resend-Signature', '')
        
        # Verify signature (optional but recommended)
        # webhook_secret = os.getenv('RESEND_WEBHOOK_SECRET')
        # if webhook_secret and not verify_resend_signature(payload, signature, webhook_secret):
        #     return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        event_type = data.get('type')
        event_data = data.get('data', {})
        
        print(f"Received Resend webhook: {event_type}")
        print(f"Event data: {event_data}")
        
        # Extract tracking information
        email_id = event_data.get('email_id')
        tags = event_data.get('tags', {})
        campaign_id = tags.get('campaign_id')
        recipient_id = tags.get('recipient_id')
        
        if not campaign_id or not recipient_id:
            print(f"Warning: Missing campaign_id or recipient_id in webhook")
            return jsonify({'status': 'ignored', 'reason': 'missing tracking data'}), 200
        
        supabase = get_supabase_admin()
        now = datetime.utcnow().isoformat()
        
        # Update recipient record based on event type
        update_data = {'updated_at': now}
        
        if event_type == 'email.sent':
            update_data['status'] = 'sent'
            update_data['sent_at'] = now
            update_data['resend_message_id'] = email_id
            
        elif event_type == 'email.delivered':
            update_data['status'] = 'delivered'
            update_data['delivered_at'] = now
            
        elif event_type == 'email.bounced':
            update_data['status'] = 'bounced'
            update_data['bounced_at'] = now
            bounce_type = event_data.get('bounce', {}).get('type')
            update_data['error_message'] = f"Bounced: {bounce_type}"
            
        elif event_type == 'email.opened':
            update_data['status'] = 'opened'
            if not event_data.get('opened_at'):
                update_data['opened_at'] = now
            # Increment open count
            result = supabase.table('email_campaign_recipients')\
                .select('open_count')\
                .eq('id', recipient_id)\
                .single()\
                .execute()
            
            if result.data:
                current_count = result.data.get('open_count', 0)
                update_data['open_count'] = current_count + 1
            
        elif event_type == 'email.clicked':
            update_data['status'] = 'clicked'
            if not event_data.get('clicked_at'):
                update_data['clicked_at'] = now
            # Increment click count
            result = supabase.table('email_campaign_recipients')\
                .select('click_count')\
                .eq('id', recipient_id)\
                .single()\
                .execute()
            
            if result.data:
                current_count = result.data.get('click_count', 0)
                update_data['click_count'] = current_count + 1
            
        elif event_type == 'email.complained':
            update_data['status'] = 'bounced'
            update_data['error_message'] = 'Marked as spam'
        
        # Update recipient record
        supabase.table('email_campaign_recipients')\
            .update(update_data)\
            .eq('id', recipient_id)\
            .execute()
        
        print(f"Updated recipient {recipient_id} for event {event_type}")
        
        # Campaign stats will auto-update via trigger
        
        return jsonify({
            'status': 'success',
            'event': event_type,
            'campaign_id': campaign_id,
            'recipient_id': recipient_id
        }), 200
        
    except Exception as e:
        print(f"Error processing Resend webhook: {e}")
        return jsonify({'error': str(e)}), 500


@webhook_bp.route('/resend/test', methods=['GET'])
def test_webhook():
    """Test endpoint to verify webhook is accessible"""
    return jsonify({
        'status': 'ok',
        'message': 'Resend webhook endpoint is active',
        'url': request.url_root + 'api/campaigns/webhooks/resend'
    }), 200
