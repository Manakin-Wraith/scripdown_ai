"""
Email Tracking Service
Logs sent emails to database for analytics and monitoring.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from db.supabase_client import SupabaseDB

# Use admin client to bypass RLS for backend email logging
db = SupabaseDB(use_admin=True)


def log_email_sent(
    email_type: str,
    recipient_email: str,
    recipient_name: str,
    resend_email_id: Optional[str] = None,
    user_status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log a sent email to the database for tracking.
    
    Args:
        email_type: Type of email ('beta_launch', 'welcome', 'reminder', etc.)
        recipient_email: Recipient's email address
        recipient_name: Recipient's full name
        resend_email_id: ID returned from Resend API
        user_status: User status ('new', 'trial', 'waitlist')
        metadata: Additional data to store as JSON
    
    Returns:
        Database insert result
    """
    try:
        data = {
            'email_type': email_type,
            'recipient_email': recipient_email,
            'recipient_name': recipient_name,
            'resend_email_id': resend_email_id,
            'user_status': user_status,
            'delivery_status': 'sent',
            'metadata': metadata or {},
            'sent_at': datetime.utcnow().isoformat()
        }
        
        result = db.client.table('email_tracking').insert(data).execute()
        return {'success': True, 'data': result.data}
    
    except Exception as e:
        print(f"Error logging email: {e}")
        return {'success': False, 'error': str(e)}


def update_email_status(
    resend_email_id: str,
    delivery_status: str,
    opened_at: Optional[str] = None,
    clicked_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update email delivery status (for webhook integration).
    
    Args:
        resend_email_id: Resend email ID
        delivery_status: New status ('delivered', 'bounced', 'failed')
        opened_at: ISO timestamp when email was opened
        clicked_at: ISO timestamp when link was clicked
    
    Returns:
        Database update result
    """
    try:
        update_data = {
            'delivery_status': delivery_status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if opened_at:
            update_data['opened_at'] = opened_at
        
        if clicked_at:
            update_data['clicked_at'] = clicked_at
        
        result = db.client.table('email_tracking')\
            .update(update_data)\
            .eq('resend_email_id', resend_email_id)\
            .execute()
        
        return {'success': True, 'data': result.data}
    
    except Exception as e:
        print(f"Error updating email status: {e}")
        return {'success': False, 'error': str(e)}


def get_email_analytics(
    email_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get email analytics and metrics.
    
    Args:
        email_type: Filter by email type (optional)
        start_date: Start date ISO string (optional)
        end_date: End date ISO string (optional)
    
    Returns:
        Analytics data with metrics
    """
    try:
        query = db.client.table('email_tracking').select('*')
        
        if email_type:
            query = query.eq('email_type', email_type)
        
        if start_date:
            query = query.gte('sent_at', start_date)
        
        if end_date:
            query = query.lte('sent_at', end_date)
        
        result = query.execute()
        emails = result.data
        
        # Calculate metrics
        total_sent = len(emails)
        delivered = len([e for e in emails if e['delivery_status'] == 'delivered'])
        bounced = len([e for e in emails if e['delivery_status'] == 'bounced'])
        opened = len([e for e in emails if e.get('opened_at')])
        clicked = len([e for e in emails if e.get('clicked_at')])
        
        return {
            'success': True,
            'metrics': {
                'total_sent': total_sent,
                'delivered': delivered,
                'bounced': bounced,
                'opened': opened,
                'clicked': clicked,
                'delivery_rate': round((delivered / total_sent * 100) if total_sent > 0 else 0, 2),
                'open_rate': round((opened / delivered * 100) if delivered > 0 else 0, 2),
                'click_rate': round((clicked / delivered * 100) if delivered > 0 else 0, 2)
            },
            'emails': emails
        }
    
    except Exception as e:
        print(f"Error getting email analytics: {e}")
        return {'success': False, 'error': str(e)}


def get_recent_emails(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get most recent sent emails.
    
    Args:
        limit: Number of emails to retrieve (default: 50)
    
    Returns:
        List of recent emails
    """
    try:
        result = db.client.table('email_tracking')\
            .select('*')\
            .order('sent_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data
    
    except Exception as e:
        print(f"Error getting recent emails: {e}")
        return []


def check_if_email_sent(recipient_email: str, email_type: str) -> bool:
    """
    Check if an email of a specific type was already sent to a recipient.
    
    Args:
        recipient_email: Recipient's email address
        email_type: Type of email to check
    
    Returns:
        True if email was already sent, False otherwise
    """
    try:
        result = db.client.table('email_tracking')\
            .select('id')\
            .eq('recipient_email', recipient_email)\
            .eq('email_type', email_type)\
            .execute()
        
        return len(result.data) > 0
    
    except Exception as e:
        print(f"Error checking email status: {e}")
        return False
