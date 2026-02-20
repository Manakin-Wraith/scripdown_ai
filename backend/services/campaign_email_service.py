"""
Campaign Email Service with Resend Tracking
Handles sending campaign emails with full tracking capabilities
"""

import os
import resend
from typing import Dict, Any, List
from datetime import datetime
from db.supabase_client import get_supabase_admin

resend.api_key = os.getenv('RESEND_API_KEY')
DEFAULT_FROM_EMAIL = os.getenv('RESEND_FROM_EMAIL', 'hello@slateone.studio')


def send_campaign_email(
    recipient_email: str,
    recipient_name: str,
    subject: str,
    html_body: str,
    text_body: str,
    campaign_id: str,
    recipient_id: str,
    template_variables: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Send a campaign email with Resend tracking
    
    Args:
        recipient_email: Recipient's email address
        recipient_name: Recipient's name
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text email body
        campaign_id: Campaign UUID for tracking
        recipient_id: Recipient record UUID for tracking
        template_variables: Variables to replace in template
    
    Returns:
        Dict with success status and Resend message ID
    """
    if not resend.api_key:
        return {
            'success': False,
            'error': 'Resend API key not configured'
        }
    
    try:
        # Replace template variables
        variables = template_variables or {}
        variables['user_name'] = recipient_name
        
        # Replace all variables in HTML and text
        final_html = html_body
        final_text = text_body
        
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            final_html = final_html.replace(placeholder, str(value))
            final_text = final_text.replace(placeholder, str(value))
        
        # Prepare email with tracking headers
        params = {
            "from": DEFAULT_FROM_EMAIL,
            "to": [recipient_email],
            "subject": subject,
            "html": final_html,
            "text": final_text,
            "tags": [
                {
                    "name": "campaign_id",
                    "value": campaign_id
                },
                {
                    "name": "recipient_id", 
                    "value": recipient_id
                }
            ],
            "headers": {
                "X-Campaign-ID": campaign_id,
                "X-Recipient-ID": recipient_id
            }
        }
        
        # Send via Resend
        response = resend.Emails.send(params)
        message_id = response.get('id') if isinstance(response, dict) else getattr(response, 'id', None)

        print(f"Campaign email sent to {recipient_email}: message_id={message_id}")

        # Write resend_message_id + status=sent back to recipient row immediately
        # so the webhook can match on recipient_id AND message_id
        if recipient_id and message_id:
            try:
                supabase = get_supabase_admin()
                supabase.table('email_campaign_recipients')\
                    .update({
                        'resend_message_id': message_id,
                        'status': 'sent',
                        'sent_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat(),
                    })\
                    .eq('id', recipient_id)\
                    .execute()
            except Exception as db_err:
                print(f"Warning: could not update recipient {recipient_id} after send: {db_err}")

        return {
            'success': True,
            'message_id': message_id,
            'recipient_email': recipient_email
        }
        
    except Exception as e:
        print(f"Error sending campaign email to {recipient_email}: {e}")
        return {
            'success': False,
            'error': str(e),
            'recipient_email': recipient_email
        }


def send_campaign_batch(
    campaign_id: str,
    template_id: str,
    recipients: List[Dict[str, Any]],
    template_variables: Dict[str, str],
    subject: str,
    html_body: str,
    text_body: str
) -> Dict[str, Any]:
    """
    Send campaign emails to multiple recipients
    
    Args:
        campaign_id: Campaign UUID
        template_id: Template UUID
        recipients: List of recipient dicts with id, email, name
        template_variables: Template variables (shared across all)
        subject: Email subject
        html_body: HTML template
        text_body: Text template
    
    Returns:
        Dict with success/failure counts and details
    """
    results = {
        'total': len(recipients),
        'sent': 0,
        'failed': 0,
        'errors': []
    }
    
    for recipient in recipients:
        result = send_campaign_email(
            recipient_email=recipient['email'],
            recipient_name=recipient.get('name', recipient['email']),
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            campaign_id=campaign_id,
            recipient_id=recipient['id'],
            template_variables=template_variables
        )
        
        if result['success']:
            results['sent'] += 1
        else:
            results['failed'] += 1
            results['errors'].append({
                'email': recipient['email'],
                'error': result.get('error')
            })
    
    return results
